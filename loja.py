"""Planta da loja CAMDA (gôndolas, estantes, expositores, balcão) e os produtos
de cada estrutura.

Porte direto de LeoLira1/Gondolas: lib/loja_scene.dart (itensLoja, referências,
rotas dos bonecos), lib/models.dart (números das estruturas, faceFromPos,
niveisProdutoPara) e lib/turso_service.dart (consultas de gondola_layout,
estante_layout e estoque_localizado). Se a planta mudar lá, copie para cá.

Sem Streamlit e sem rede, para poder ser testado.
"""

from __future__ import annotations

import math
from typing import Any

# ── Planta (loja_scene.dart) ────────────────────────────────────────────────
LOJA_W = 10.0
LOJA_H = 14.0
PAREDE_ESP = 0.18
PAREDE_H = 0.90

# Números das estruturas (models.dart)
EDR300 = 8
EDR300_TRIPLA = 6
MAGNOJET = 9
NELLORE = 19
MONITOR = 20
BALCAO = 21
PAREDE_MIN, PAREDE_MAX = 13, 18
ESTANTES_REMOVIDAS = (3, 4)
PALETE_MIN = 101
# Ilha de paletes: 12 paletes com tapume verde no corredor central, 2 de largura × 6 de comprimento,
# 5 produtos por palete. No banco é a estante 22 com nivel = espaço (0–11) e coluna = produto (0–4).
ILHA = 22
ESPACOS_ILHA = 12
COLUNAS_ESPACOS_ILHA = 2
PRODUTOS_POR_ESPACO_ILHA = 5
# Mostruário: palete de madeira (1,20 × 1,00 m) na parede da direita, entre a E1 e a cozinha, com ~20 tipos
# de ferragem e ferramenta. No banco é a estante 23 com nivel = posição (0–19) e coluna sempre 0.
MOSTRUARIO = 23
POSICOES_MOSTRUARIO = 20
# Expositor de Madeira: escada maciça de 3 degraus (1 m × 1 m) encostada no balcão pelo lado do corredor, 6 produtos
# por degrau. No banco é a estante 24 com nivel = degrau (0 = de baixo) e coluna = produto (0–5), letras A–F no degrau
# de cima, G–L no do meio e M–R no de baixo.
MADEIRA = 24
DEGRAUS_MADEIRA = ("de baixo", "do meio", "de cima")

GONDOLA_R = 0.62
# (raio, y do centro, altura) de cada prateleira da gôndola, na escala da cena de detalhe
GONDOLA_PRATELEIRAS = ((3.4, 0.675, 0.35), (2.4, 2.15, 0.30), (1.5, 3.43, 0.26))
GONDOLA_ESCALA = GONDOLA_R / 3.4
ALTURA_GONDOLA = (3.43 + 0.26 / 2) * GONDOLA_ESCALA
ESTANTE_H = 0.85

# Cada item: (tipo, numero, x, z, w, d). Os 12 primeiros são gôndolas.
_G = [(12, 3, 4), (7, 5, 4), (5, 7, 4), (11, 3, 6), (4, 7, 6), (10, 3, 8),
      (3, 7, 8), (9, 3, 10), (2, 7, 10), (8, 3, 12), (6, 5, 12), (1, 7, 12)]

_BALCAO_Z = LOJA_H - PAREDE_ESP - 7.95 / 2

_ESTRUTURAS = (
    # (numero, x, z, w, d)
    (7, 1.00, 1.0, 0.7, 1.6),
    (8, 2.10, 0.55, 1.4, 0.7),
    (9, 6.45, 0.55, 1.05, 0.55),
    (6, 3.20, 1.0, 0.7, 1.6),
    (MONITOR, 4.20, 0.55, 1.14, 0.62),
    (NELLORE, 5.35, 0.55, 0.85, 0.55),
    (2, 9.45, 2.0, 0.7, 1.6),
    (1, 9.45, 4.0, 0.7, 1.6),
    (PAREDE_MIN, 0.45, 10.6, 0.55, 4.4),
    (BALCAO, 1.45, _BALCAO_Z, 0.60, 7.95),
    # Medida de mapa, não a real (2,40 × 6,00 m): na planta simplificada a ilha real encostaria nas gôndolas.
    (ILHA, 5.0, 8.0, 1.8, 5.6),
    # Medida real, com o lado de 1,20 m ao longo da parede; o corredor do cliente (x = 8,4) passa pela frente.
    (MOSTRUARIO, 9.27, 6.2, 1.0, 1.2),
    # Colado no balcão (borda em x = 1,75), no vão entre a G9 (z = 10) e a G8 (z = 12); 0,40 m de fundo × 1 m.
    (MADEIRA, 1.45 + 0.30 + 0.20, 11.0, 0.40, 1.0),
)

REFERENCIAS = (
    ("CAIXA", 5.0, 0.80, False),
    ("BALCÃO LOJA", 0.9, 8.00, False),
    ("COZINHA", 9.2, 8.00, False),
    ("ENTRADA", 7.5, 13.91, True),
    ("ENTRADA 2", 2.5, 13.91, True),
)

# Rotas dos bonecos (rotasLoja): funcionário e cliente, só pelos corredores. O funcionário
# dá a volta na ilha de paletes, entre ela e as colunas de gôndolas. O cliente desvia do Expositor de Madeira
# por x = 2,38, no vão entre a G9 e a G8.
ROTAS = (
    ((3.86, 4.91), (3.86, 12.85), (6.14, 12.85), (6.14, 4.91)),
    ((8.4, 2.80), (8.4, 13.30), (2.05, 13.30), (2.05, 11.90), (2.38, 11.50), (2.38, 10.50), (2.05, 10.10),
     (2.05, 2.80)),
)


def _kind(numero: int) -> str:
    if numero == EDR300_TRIPLA:
        return "edr300x3"
    if numero == EDR300:
        return "edr300"
    if numero == MAGNOJET:
        return "magnojet"
    if numero == NELLORE:
        return "nellore"
    if numero == MONITOR:
        return "monitor"
    if numero == BALCAO:
        return "balcao"
    if numero == ILHA:
        return "ilha"
    if numero == MOSTRUARIO:
        return "mostruario"
    if numero == MADEIRA:
        return "madeira"
    if PAREDE_MIN <= numero <= PAREDE_MAX:
        return "parede"
    return "estante"


def _itens() -> list[dict[str, Any]]:
    itens: list[dict[str, Any]] = []
    for numero, x, z in _G:
        itens.append({"tipo": "gondola", "n": numero, "x": float(x), "z": float(z), "w": 0.7, "d": 1.6, "kind": "gondola"})
    for numero, x, z, w, d in _ESTRUTURAS:
        itens.append({"tipo": "estante", "n": numero, "x": x, "z": z, "w": w, "d": d, "kind": _kind(numero)})
    return itens


ITENS = _itens()


def numero_no_mapa(tipo: str, numero: int) -> int:
    """As 6 seções da Estante Parede (13–18) são um retângulo só, o da seção 13."""
    return PAREDE_MIN if tipo == "estante" and PAREDE_MIN <= numero <= PAREDE_MAX else numero


def rotulo_curto(item: dict[str, Any]) -> str:
    if item["kind"] == "balcao":
        return "Balcão"
    if item["kind"] == "parede":
        return "E13–18"
    if item["kind"] == "ilha":
        return "Ilha"
    if item["kind"] == "mostruario":
        return "Mostruário"
    return ("G" if item["tipo"] == "gondola" else "E") + str(item["n"])


def nome_estrutura(item: dict[str, Any]) -> str:
    k = item["kind"]
    if k == "balcao":
        return "Balcão de Atendimento"
    if k == "parede":
        return "Estante Parede (seções 13–18)"
    if k == "magnojet":
        return "Expositor MagnoJet (E9)"
    if k == "nellore":
        return "Expositor Nellore (E19)"
    if k == "monitor":
        return "Expositor Monitor (E20)"
    if k == "ilha":
        return "Ilha de paletes (12 espaços × 5 produtos)"
    if k == "mostruario":
        return "Mostruário de ferragens (20 posições)"
    if k == "madeira":
        return "Expositor de Madeira (E24 · 3 degraus × 6)"
    return ("Gôndola " if item["tipo"] == "gondola" else "Estante ") + str(item["n"])


# ── Endereços (models.dart) ─────────────────────────────────────────────────


def _dart_round(v: float) -> int:
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


def face_from_pos(px: float, pz: float) -> int:
    """Face 1–6 da gôndola, derivada de pos_x/pos_z (face 1 = voltada para +Z)."""
    ang = math.atan2(pz, px) * 180 / math.pi
    k = _dart_round((90 - ang) / 60) % 6
    return k + 1


def niveis_produto(numero: int) -> int:
    """niveisProdutoPara: quantos níveis a estante tem (para limitar o nível lido)."""
    if numero >= PALETE_MIN:
        return 3
    if numero == ILHA:
        return ESPACOS_ILHA
    if numero == MOSTRUARIO:
        return POSICOES_MOSTRUARIO
    if numero in (EDR300, EDR300_TRIPLA):
        return 6
    if numero == MAGNOJET:
        return 7
    if numero == NELLORE:
        return 6
    if numero == MONITOR:
        return 4
    if numero == MADEIRA:
        return len(DEGRAUS_MADEIRA)
    if PAREDE_MIN <= numero <= PAREDE_MAX:
        return 6
    if numero in (3, 4):
        return 5
    return 4


ANDARES = ("Base", "Meio", "Topo")


def faixas(item: dict[str, Any]) -> int:
    """Quantas "vagas" de endereço a estrutura tem, para a capacidade da loja.

    Gôndola: 3 andares × 6 faces = 18. Estante: um por nível (o banco guarda o nível; a coluna não entra
    na conta). Estante Parede: 6 seções × 6 níveis. Ilha de paletes: um por espaço (12). Mostruário: um por posição (20). A base do Nellore (nível 0) saiu dos endereços.
    O balcão não tem endereço.
    """
    k = item["kind"]
    if k == "balcao":
        return 0
    if k == "gondola":
        return len(ANDARES) * 6
    if k == "parede":
        return (PAREDE_MAX - PAREDE_MIN + 1) * niveis_produto(PAREDE_MIN)
    if k == "nellore":
        return niveis_produto(NELLORE) - 1
    return niveis_produto(item["n"])


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def montar(
    gondolas: list[dict[str, Any]],
    estantes: list[dict[str, Any]],
    quantidades: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cruza gondola_layout, estante_layout e estoque_localizado e devolve o JSON da cena."""
    # Somas por endereço (o prefixo por TIPO evita misturar números iguais de tipos diferentes)
    somas: dict[tuple, float] = {}
    for r in quantidades:
        tipo = r.get("local_tipo") or ""
        cod = (r.get("produto_codigo") or "")
        num = int(r.get("local_num") or 0)
        fc = int(r.get("face_ou_coluna") or 0)
        an = int(r.get("andar_ou_nivel") or 0)
        q = _num(r.get("quantidade"))
        if tipo == "gondola":
            chave = ("g", cod, num, fc, an)
        elif tipo in ("galpao", "barracao"):
            continue
        elif num == ILHA:
            # Na ilha a posição é espaço + produto: a coluna separa os 5 produtos do mesmo espaço.
            chave = ("e", cod, num, _clamp(an, 0, ESPACOS_ILHA - 1), _clamp(fc, 0, PRODUTOS_POR_ESPACO_ILHA - 1))
        else:
            chave = ("e", cod, num, _clamp(an, 0, niveis_produto(num) - 1))
        somas[chave] = somas.get(chave, 0.0) + q

    por_item: dict[tuple[str, int], list[dict[str, Any]]] = {}
    vistos: set = set()
    for r in gondolas:
        cod = r.get("produto_codigo") or ""
        num = int(r.get("gondola_num") or 0)
        a = _clamp(int(r.get("andar") or 0), 0, 2)
        face = face_from_pos(_num(r.get("pos_x")), _num(r.get("pos_z")))
        if (cod, num, a, face) in vistos:
            continue
        vistos.add((cod, num, a, face))
        por_item.setdefault(("gondola", num), []).append(
            {"c": cod, "n": r.get("produto_nome") or "", "loc": f"Face {face} · {ANDARES[a]}",
             "q": somas.get(("g", cod, num, face, a)), "o": a * 10 + face, "k": (a, face)}
        )
    vistos = set()
    for r in estantes:
        cod = r.get("produto_codigo") or ""
        num = int(r.get("estante_num") or 0)
        if num in ESTANTES_REMOVIDAS or (num == NELLORE and int(r.get("nivel") or 0) == 0):
            continue
        niv = _clamp(int(r.get("nivel") or 0), 0, niveis_produto(num) - 1)
        if num == ILHA:
            col = _clamp(int(r.get("coluna") or 0), 0, PRODUTOS_POR_ESPACO_ILHA - 1)
            if (cod, num, niv, col) in vistos:
                continue
            vistos.add((cod, num, niv, col))
            # Endereço espaço-produto, como no app: 3-2 é o produto 2 do espaço 3.
            por_item.setdefault(("estante", num), []).append(
                {"c": cod, "n": r.get("produto_nome") or "", "loc": f"Espaço {niv + 1} · produto {col + 1}",
                 "q": somas.get(("e", cod, num, niv, col)), "o": niv * 10 + col, "k": (num, niv)}
            )
            continue
        if (cod, num, niv) in vistos:
            continue
        vistos.add((cod, num, niv))
        no_mapa = numero_no_mapa("estante", num)
        if num == MOSTRUARIO:
            loc = f"Posição {niv + 1}"                            # o nível é a posição 1–20 no tampo
        elif num == MADEIRA:
            loc = f"Degrau {DEGRAUS_MADEIRA[niv]}"
        elif no_mapa == num:
            loc = f"Nível {niv + 1}"
        else:
            loc = f"Seção {num} · Nível {niv + 1}"
        por_item.setdefault(("estante", no_mapa), []).append(
            {"c": cod, "n": r.get("produto_nome") or "", "loc": loc,
             "q": somas.get(("e", cod, num, niv)), "o": num * 10 + niv, "k": (num, niv)}
        )

    catalogo: dict[str, str] = {}
    itens = []
    for it in ITENS:
        prods = sorted(por_item.get((it["tipo"], it["n"]), []), key=lambda p: (p["o"], p["n"]))
        ocupadas = len({p["k"] for p in prods})                   # faixas com ao menos um produto
        for p in prods:
            p.pop("o")
            p.pop("k")
            if p["c"].strip():
                catalogo.setdefault(p["c"], p["n"])
        itens.append({**it, "rot": rotulo_curto(it), "nome": nome_estrutura(it), "prod": prods,
                      "faixas": faixas(it), "ocupadas": min(ocupadas, faixas(it))})

    return {
        "loja": {"w": LOJA_W, "h": LOJA_H, "parede": PAREDE_ESP, "paredeH": PAREDE_H},
        "gondola": {"r": GONDOLA_R, "prat": [list(p) for p in GONDOLA_PRATELEIRAS], "escala": GONDOLA_ESCALA},
        "estanteH": ESTANTE_H,
        "ilha": {"colunas": COLUNAS_ESPACOS_ILHA, "espacos": ESPACOS_ILHA},
        "alturaBoneco": ALTURA_GONDOLA,
        "itens": itens,
        "refs": [{"nome": n, "x": x, "z": z, "parede": p} for n, x, z, p in REFERENCIAS],
        "rotas": [[list(p) for p in r] for r in ROTAS],
        "catalogo": [{"c": c, "n": n} for c, n in sorted(catalogo.items())],
    }
