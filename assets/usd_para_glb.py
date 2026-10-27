"""Converte um asset SimReady (OpenUSD) num .glb cru para a web.

Uso: python assets/usd_para_glb.py entrada.usd saida.glb

- Lê só o que o three.js entende: malhas, UV `st`, normais e o material UsdPreviewSurface
  (o MDL da Omniverse é ignorado).
- Z para cima (USD) vira Y para cima (glTF), em metros.
- Texturas UDIM (`<UDIM>`, tiles 1001…100N numa linha) viram um atlas só, com o U dividido por N,
  porque o glTF não tem UDIM.
- A malha sai sem simplificar; quem enxuga é o gltfpack (ver assets/converter_simready.sh).
"""
import glob
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from pxr import Usd, UsdGeom, UsdShade

LADO_MAX = 2048  # maior lado de textura que vai para o navegador
Z_PARA_Y = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)  # (x, y, z) -> (x, z, -y)


def _textura(entrada):
    """UsdUVTexture ligado a um input do PreviewSurface: (shader, canal de saída) ou None."""
    if not entrada or not entrada.HasConnectedSource():
        return None
    fonte, saida, _ = entrada.GetConnectedSource()
    sh = UsdShade.Shader(fonte.GetPrim())
    if sh.GetIdAttr().Get() != "UsdUVTexture":
        return None
    return sh, saida


def _arquivo(sh):
    """Caminho do arquivo do UsdUVTexture, ancorado na camada onde ele foi escrito."""
    attr = sh.GetInput("file").GetAttr()
    caminho = attr.Get().path
    camada = attr.GetPropertyStack(Usd.TimeCode.Default())[0].layer
    return str((Path(camada.realPath).parent / caminho).resolve())


_cache_img = {}


def _imagem(caminho):
    """(PIL.Image, n_tiles). UDIM vira atlas horizontal com n_tiles tiles; arquivo comum tem n_tiles = 1."""
    if caminho in _cache_img:
        return _cache_img[caminho]
    if "<UDIM>" in caminho:
        tiles = sorted(glob.glob(caminho.replace("<UDIM>", "1[0-9][0-9][0-9]")))
        idx = [int(re.search(r"\.(1\d{3})\.", t).group(1)) - 1001 for t in tiles]
        if any(i >= 10 for i in idx):
            raise SystemExit(f"UDIM com mais de uma linha não suportado: {caminho}")
        n = max(idx) + 1
        lado = Image.open(tiles[0]).size[0]
        atlas = Image.new("RGB", (lado * n, lado))
        for t, i in zip(tiles, idx):
            atlas.paste(Image.open(t).convert("RGB").resize((lado, lado)), (i * lado, 0))
        img = atlas
    else:
        img, n = Image.open(caminho).convert("RGB"), 1
    if max(img.size) > LADO_MAX:
        f = LADO_MAX / max(img.size)
        img = img.resize((max(1, round(img.size[0] * f)), max(1, round(img.size[1] * f))), Image.LANCZOS)
    _cache_img[caminho] = (img, n)
    return img, n


def _cor_exibicao(malha):
    pv = UsdGeom.PrimvarsAPI(malha).GetPrimvar("displayColor")
    cor = pv.ComputeFlattened() if pv else None
    return [float(c) for c in cor[0]] if cor is not None and len(cor) else [0.5, 0.5, 0.5]


def _cor_mdl(mat):
    """Cor chapada do OmniPBR (MDL), sem textura. Nas variações de cor da SimReady (ex.: blue_a01) só o MDL
    tem a cor certa; o UsdPreviewSurface ficou com a cor do modelo de origem."""
    sh = mat.ComputeSurfaceSource("mdl")[0]
    if not sh or sh.GetPrim().GetAttribute("info:mdl:sourceAsset:subIdentifier").Get() != "OmniPBR":
        return None
    tex = sh.GetInput("diffuse_texture")
    if tex and tex.Get() and tex.Get().path:
        return None
    cor = sh.GetInput("diffuse_color_constant")
    return cor.Get() if cor else None


_cache_mat = {}


def _material(prim, malha):
    """(trimesh PBRMaterial, n_tiles do UDIM usado no UV). `prim` é a malha ou um GeomSubset dela."""
    mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    chave = str(mat.GetPath()) if mat else "cor:" + ",".join(f"{c:.3f}" for c in _cor_exibicao(malha))
    if chave in _cache_mat:
        return _cache_mat[chave]
    sup = mat.ComputeSurfaceSource()[0] if mat else None
    if not sup or sup.GetIdAttr().Get() != "UsdPreviewSurface":
        res = (trimesh.visual.material.PBRMaterial(
            name=chave, baseColorFactor=_cor_exibicao(malha) + [1.0],
            metallicFactor=0.0, roughnessFactor=0.7), 1)
        _cache_mat[chave] = res
        return res

    def const(nome, padrao):
        e = sup.GetInput(nome)
        v = e.Get() if e and not e.HasConnectedSource() else None
        return padrao if v is None else v

    kw = {"name": mat.GetPrim().GetName(), "doubleSided": False}
    tiles = 1
    cor = _textura(sup.GetInput("diffuseColor"))
    if cor:
        kw["baseColorTexture"], tiles = _imagem(_arquivo(cor[0]))
    else:
        kw["baseColorFactor"] = [*map(float, _cor_mdl(mat) or const("diffuseColor", (0.8, 0.8, 0.8))), 1.0]
    opac = float(const("opacity", 1.0))
    if opac < 1.0:
        kw.setdefault("baseColorFactor", [1.0, 1.0, 1.0, 1.0])[3] = opac
        kw["alphaMode"] = "BLEND"
    met, rug = _textura(sup.GetInput("metallic")), _textura(sup.GetInput("roughness"))
    if met and rug and _arquivo(met[0]) == _arquivo(rug[0]) and (met[1], rug[1]) == ("b", "g"):
        # ORM: R = oclusão, G = rugosidade, B = metal — o mesmo arranjo do glTF
        kw["metallicRoughnessTexture"], _ = _imagem(_arquivo(met[0]))
        kw["metallicFactor"] = kw["roughnessFactor"] = 1.0
    else:
        kw["metallicFactor"] = float(const("metallic", 0.0))
        kw["roughnessFactor"] = float(const("roughness", 0.5))
    nor = _textura(sup.GetInput("normal"))
    if nor:
        kw["normalTexture"], _ = _imagem(_arquivo(nor[0]))
    res = (trimesh.visual.material.PBRMaterial(**kw), tiles)
    _cache_mat[chave] = res
    return res


def _triangular(contagens):
    """Índices de canto (face-varying) em leque: cada polígono de n lados vira n-2 triângulos.
    Devolve também o polígono de origem de cada triângulo (para os GeomSubset de material)."""
    contagens = np.asarray(contagens)
    inicio = np.concatenate([[0], np.cumsum(contagens)[:-1]])
    tri = [np.stack([np.full(n - 2, s), s + np.arange(1, n - 1), s + np.arange(2, n)], axis=1)
           for s, n in zip(inicio, contagens) if n >= 3]
    origem = np.repeat(np.arange(len(contagens)), np.maximum(contagens - 2, 0))
    return np.concatenate(tri), origem


def _por_canto(primvar, interp, indices_vert, n_cantos):
    dados = np.asarray(primvar, dtype=np.float64)
    if interp == "faceVarying":
        return dados
    if interp in ("vertex", "varying"):
        return dados[indices_vert]
    if interp == "constant":
        return np.repeat(dados[:1], n_cantos, axis=0)
    raise ValueError(f"interpolação não suportada: {interp}")


def converter(entrada, saida):
    palco = Usd.Stage.Open(str(entrada))
    if UsdGeom.GetStageUpAxis(palco) != UsdGeom.Tokens.z:
        raise SystemExit("esperava Z para cima")
    escala = UsdGeom.GetStageMetersPerUnit(palco)
    xf = UsdGeom.XformCache(Usd.TimeCode.Default())
    cena = trimesh.Scene()
    total = 0
    for prim in Usd.PrimRange(palco.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility() == "invisible":
            continue
        if UsdGeom.Imageable(prim).ComputePurpose() not in ("default", "render"):
            continue
        m = UsdGeom.Mesh(prim)
        pts = np.asarray(m.GetPointsAttr().Get(), dtype=np.float64)
        cont, idx = m.GetFaceVertexCountsAttr().Get(), np.asarray(m.GetFaceVertexIndicesAttr().Get())
        if pts.size == 0 or not cont:
            continue
        mundo = np.array(xf.GetLocalToWorldTransform(prim), dtype=np.float64).T  # USD usa vetor-linha
        rot = Z_PARA_Y @ mundo[:3, :3]
        p = (pts[idx] @ rot.T + Z_PARA_Y @ mundo[:3, 3]) * escala

        nrm = m.GetNormalsAttr().Get()
        n = None
        if nrm is not None and len(nrm):
            n = _por_canto(nrm, m.GetNormalsInterpolation(), idx, len(idx)) @ np.linalg.inv(rot).T
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        pv = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
        uv = _por_canto(pv.ComputeFlattened(), pv.GetInterpolation(), idx, len(idx)) if pv and pv.HasValue() else None

        idx_tri, origem = _triangular(cont)
        if (np.linalg.det(rot) < 0) != (m.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded):
            idx_tri = idx_tri[:, ::-1]
        # material da malha toda + um por GeomSubset (familyType materialBind)
        partes, livre = [], np.ones(len(cont), dtype=bool)
        for sub in UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets():
            faces = np.asarray(sub.GetIndicesAttr().Get() or [], dtype=np.int64)
            livre[faces] = False
            partes.append((sub.GetPrim(), np.isin(origem, faces)))
        if livre.any():
            partes.append((prim, livre[origem]))
        for alvo, sel in partes:
            if not sel.any():
                continue
            material, tiles = _material(alvo, m)
            cantos = np.unique(idx_tri[sel])
            novo = np.full(len(idx), -1, dtype=np.int64)
            novo[cantos] = np.arange(len(cantos))
            uv_p = None
            if uv is not None:
                uv_p = uv[cantos].copy()
                uv_p[:, 0] /= tiles
            visual = trimesh.visual.TextureVisuals(uv=uv_p, material=material)
            malha = trimesh.Trimesh(vertices=p[cantos], faces=novo[idx_tri[sel]],
                                    vertex_normals=None if n is None else n[cantos], visual=visual, process=False)
            cena.add_geometry(malha, node_name=f"{prim.GetParent().GetName()}_{alvo.GetName()}",
                              geom_name=f"{prim.GetName()}_{alvo.GetName()}")
            total += int(sel.sum())
    cena.export(str(saida))
    print(f"{Path(entrada).name}: {len(cena.geometry)} malhas, {total} triângulos -> {saida}")


if __name__ == "__main__":
    converter(sys.argv[1], sys.argv[2])
