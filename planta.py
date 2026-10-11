"""Planta geral: onde cada prédio fica em relação aos outros, e o barracão.

A disposição segue o croqui da loja (planta baixa desenhada à mão): a loja embaixo,
o Galpão Parte 1 logo acima dela, o corredor de carregamento (que continua no
corredor da loja, com o portão na ponta de baixo) à esquerda dos dois, e o Galpão
Parte 2 à esquerda do corredor. O barracão fica ao norte do Galpão Parte 1.

O croqui não tem escala: os galpões são dimensionados pelo envelope dos racks
(planta do Gondolas, em metros) mais uma margem, e a loja e o barracão têm as
medidas reais do Gondolas (10 × 14 m e 35 × 10 m). Tudo que é palpite está em
constantes aqui no topo, para ajustar num lugar só.

Barracão: porte de lib/barracao_config.dart do Gondolas (tabela barracao_enderecos,
em CENTÍMETROS; aqui convertido para metros).
"""

from __future__ import annotations

from typing import Any

import galpao as g
import loja as lj

# ── Palpites do croqui (metros) ─────────────────────────────────────────────
MARGEM_GALPAO = 1.0        # folga entre os racks e a parede do galpão
PAREDE_GALPAO = 0.20
LARGURA_CORREDOR = 4.0     # corredor da loja / corredor de carregamento
PATIO_BARRACAO = 4.0       # vão entre o Galpão Parte 1 e o barracão

# ── Barracão (barracao_config.dart, centímetros) ────────────────────────────
B_LARGURA, B_PROF, B_PE_DIREITO, B_ESP = 3500.0, 1000.0, 600.0, 20.0
B_ABERTURAS = (  # (tipo, x0, x1, altura) na parede da frente (z = 0)
    ("PORTA", 600.0, 800.0, 300.0),
    ("PORTÃO", 1300.0, 1800.0, 450.0),
    ("PORTA", 2300.0, 2500.0, 300.0),
)
PALETE_X, PALETE_Z, PALETE_H = 120.0, 100.0, 15.0
BAG_X, BAG_Z, BAG_H = 100.0, 85.0, 130.0
PASSO_X, PASSO_Z, RECUO_ABERTURAS = 135.0, 120.0, 120.0
FILEIRAS_POR_LADO = 2


def _b_interior() -> tuple[float, float, float, float]:
    return B_ESP, B_LARGURA - B_ESP, B_ESP, B_PROF - B_ESP


def b_colunas() -> int:
    x0, x1, _, _ = _b_interior()
    disp = (x1 - x0) - PALETE_X
    return 0 if disp < 0 else 1 + int(disp // PASSO_X)


def b_z_da_fileira(i: int) -> float:
    _, _, z0, z1 = _b_interior()
    if i < FILEIRAS_POR_LADO:
        return z1 - PALETE_Z / 2 - i * PASSO_Z
    idx_frente = FILEIRAS_POR_LADO * 2 - 1 - i
    return z0 + RECUO_ABERTURAS + PALETE_Z / 2 + idx_frente * PASSO_Z


def b_x_da_coluna(j: int) -> float:
    x0, x1, _, _ = _b_interior()
    n = b_colunas()
    ocupado = PALETE_X + (n - 1) * PASSO_X
    margem = ((x1 - x0) - ocupado) / 2
    return x0 + margem + PALETE_X / 2 + j * PASSO_X


def b_posicoes_padrao() -> list[dict[str, Any]]:
    """Layout padrão (BarracaoConfig.posicoesPadrao): 4 fileiras × 25, BAR-01…BAR-100."""
    lista: list[dict[str, Any]] = []
    for fileira in range(FILEIRAS_POR_LADO * 2):
        for coluna in range(b_colunas()):
            lista.append({"rot": f"BAR-{len(lista) + 1:02d}", "x": b_x_da_coluna(coluna), "z": b_z_da_fileira(fileira)})
    return lista


# ── Disposição dos prédios ──────────────────────────────────────────────────


def disposicao() -> dict[str, Any]:
    """Retângulos (x0, x1, z0, z1) de cada prédio e corredor, em metros. x leste, z sul."""
    pred: dict[str, dict[str, Any]] = {}
    pred["loja"] = {"nome": "LOJA", "x0": 0.0, "x1": lj.LOJA_W, "z0": 0.0, "z1": lj.LOJA_H}

    off: dict[int, tuple[float, float]] = {}
    tamanho: dict[int, tuple[float, float]] = {}
    for parte in g.PARTES:
        mnx, mxx, mnz, mxz = g.limites_da_parte(parte)
        tamanho[parte] = ((mxx - mnx) + 2 * MARGEM_GALPAO, (mxz - mnz) + 2 * MARGEM_GALPAO)
    w1, h1 = tamanho[1]
    w2, h2 = tamanho[2]
    # Parte 1: acima da loja, com a parede oeste alinhada à da loja (o corredor segue reto).
    pred["galpao1"] = {"nome": "GALPÃO PARTE 1", "x0": 0.0, "x1": w1, "z0": -h1, "z1": 0.0}
    # Parte 2: à esquerda do corredor, com a parede sul alinhada à da Parte 1.
    pred["galpao2"] = {"nome": "GALPÃO PARTE 2", "x0": -LARGURA_CORREDOR - w2, "x1": -LARGURA_CORREDOR, "z0": -h2, "z1": 0.0}
    for parte, chave in ((1, "galpao1"), (2, "galpao2")):
        mnx, mxx, mnz, mxz = g.limites_da_parte(parte)
        p = pred[chave]
        cx, cz = (p["x0"] + p["x1"]) / 2, (p["z0"] + p["z1"]) / 2
        off[parte] = (cx - (mnx + mxx) / 2, cz - (mnz + mxz) / 2)

    topo_galpoes = -max(h1, h2)
    bz1 = -h1 - PATIO_BARRACAO                    # parede da frente (sul) do barracão
    pred["barracao"] = {"nome": "BARRACÃO", "x0": 0.0, "x1": B_LARGURA / 100, "z0": bz1 - B_PROF / 100, "z1": bz1}

    corredores = [
        {"nome": "CORREDOR CARREGAMENTO", "x0": -LARGURA_CORREDOR, "x1": 0.0, "z0": topo_galpoes, "z1": 0.0},
        {"nome": "CORREDOR DA LOJA", "x0": -LARGURA_CORREDOR, "x1": 0.0, "z0": 0.0, "z1": lj.LOJA_H},
        {"nome": "PÁTIO", "x0": 0.0, "x1": B_LARGURA / 100, "z0": bz1, "z1": -h1},
    ]
    todos = list(pred.values()) + corredores
    limites = {
        "x0": min(r["x0"] for r in todos), "x1": max(r["x1"] for r in todos),
        "z0": min(r["z0"] for r in todos), "z1": max(r["z1"] for r in todos),
    }
    return {
        "predios": pred, "corredores": corredores, "limites": limites,
        "portao": {"x": -LARGURA_CORREDOR / 2, "z": lj.LOJA_H, "larg": LARGURA_CORREDOR},
        "parede_galpao": PAREDE_GALPAO,
        "off": {str(k): list(v) for k, v in off.items()},
    }


def montar_barracao(linhas: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Barracão em metros. `linhas` = barracao_enderecos; sem linhas, o layout padrão (todos livres)."""
    padrao = not linhas
    pal = []
    if linhas:
        for r in linhas:
            pal.append({
                "id": r.get("id"), "rot": r.get("rotulo") or "", "x": float(r.get("pos_x") or 0) / 100,
                "z": float(r.get("pos_z") or 0) / 100, "c": r.get("produto_codigo") or "",
                "n": r.get("produto_nome") or "", "q": float(r.get("quantidade") or 0),
            })
    else:
        for i, p in enumerate(b_posicoes_padrao()):
            pal.append({"id": None, "rot": p["rot"], "x": p["x"] / 100, "z": p["z"] / 100, "c": "", "n": "", "q": 0.0})
    return {
        "padrao": padrao,
        "w": B_LARGURA / 100, "d": B_PROF / 100, "h": B_PE_DIREITO / 100, "esp": B_ESP / 100,
        "aberturas": [{"tipo": t, "x0": a / 100, "x1": b / 100, "h": h / 100} for t, a, b, h in B_ABERTURAS],
        "palete": {"x": PALETE_X / 100, "z": PALETE_Z / 100, "h": PALETE_H / 100},
        "bag": {"x": BAG_X / 100, "z": BAG_Z / 100, "h": BAG_H / 100},
        "pal": pal,
    }
