"""Barracão da CAMDA: planta (35 × 10 m) e endereços de palete.

Porte de LeoLira1/Gondolas: lib/barracao_config.dart (medidas, aberturas, layout padrão),
lib/barracao_service.dart e a tabela barracao_enderecos (turso_service.dart). No Gondolas o
barracão inteiro trabalha em CENTÍMETROS; aqui o JSON da cena sai em METROS.

Sem Streamlit e sem rede, para poder ser testado.
"""

from __future__ import annotations

from typing import Any

from estocados import catalogo_da_cena, codigo_eh_estocado

# ── Obra (centímetros) ──────────────────────────────────────────────────────
LARGURA = 3500.0          # X: a parede das aberturas tem esta medida
PROFUNDIDADE = 1000.0     # Z: da parede das aberturas (z = 0) à do fundo
PE_DIREITO = 600.0
ESPESSURA = 20.0

# Aberturas, todas na parede da frente (z = 0): (tipo, x0, x1, altura do vão)
ABERTURAS = (
    ("PORTA", 600.0, 800.0, 300.0),
    ("PORTÃO", 1300.0, 1800.0, 450.0),
    ("PORTA", 2300.0, 2500.0, 300.0),
)

# Palete de madeira e bag de 1000 kg em cima
PALETE_X, PALETE_Z, PALETE_H = 120.0, 100.0, 15.0
BAG_X, BAG_Z, BAG_H = 100.0, 85.0, 130.0

# Layout padrão (semente da tabela barracao_enderecos)
PASSO_X = 135.0           # palete 120 + folga 15
PASSO_Z = 120.0           # palete 100 + folga 20
CORREDOR_MANOBRA = 400.0
FILEIRAS_POR_LADO = 2
RECUO_ABERTURAS = 120.0
FILEIRAS = FILEIRAS_POR_LADO * 2

_X0, _X1 = ESPESSURA, LARGURA - ESPESSURA
_Z0, _Z1 = ESPESSURA, PROFUNDIDADE - ESPESSURA


def colunas() -> int:
    """Quantos paletes cabem numa fileira, entre as duas paredes laterais."""
    disponivel = (_X1 - _X0) - PALETE_X
    return 0 if disponivel < 0 else 1 + int(disponivel // PASSO_X)


def z_da_fileira(i: int) -> float:
    """Z do centro da fileira i, numerada do fundo para a frente."""
    if i < FILEIRAS_POR_LADO:
        return _Z1 - PALETE_Z / 2 - i * PASSO_Z
    idx_frente = FILEIRAS - 1 - i
    return _Z0 + RECUO_ABERTURAS + PALETE_Z / 2 + idx_frente * PASSO_Z


def x_da_coluna(j: int) -> float:
    """X do centro da coluna j, com a grade centrada entre as laterais."""
    n = colunas()
    ocupado = PALETE_X + (n - 1) * PASSO_X
    margem = ((_X1 - _X0) - ocupado) / 2
    return _X0 + margem + PALETE_X / 2 + j * PASSO_X


def corredor_livre() -> float:
    fundo = z_da_fileira(FILEIRAS_POR_LADO - 1) - PALETE_Z / 2
    frente = z_da_fileira(FILEIRAS_POR_LADO) + PALETE_Z / 2
    return fundo - frente


def rotulo_do_indice(i: int) -> str:
    """BAR-01, BAR-02 … BAR-100: sequência contínua no barracão inteiro."""
    return f"BAR-{i + 1:02d}"


def posicoes_padrao() -> list[dict[str, Any]]:
    """Duas fileiras de cada lado do corredor central, do fundo para a frente."""
    lista: list[dict[str, Any]] = []
    for fileira in range(FILEIRAS):
        for coluna in range(colunas()):
            lista.append({"rot": rotulo_do_indice(len(lista)), "x": x_da_coluna(coluna), "z": z_da_fileira(fileira)})
    return lista


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def montar(linhas: list[dict[str, Any]] | None) -> dict[str, Any]:
    """JSON da cena, em metros. `linhas` = barracao_enderecos; sem linhas, o layout padrão (tudo livre)."""
    padrao = not linhas
    pal: list[dict[str, Any]] = []
    if linhas:
        for r in linhas:
            pal.append({
                "id": r.get("id"), "rot": r.get("rotulo") or "",
                "x": _num(r.get("pos_x")) / 100, "z": _num(r.get("pos_z")) / 100,
                "c": r.get("produto_codigo") or "", "n": r.get("produto_nome") or "",
                "q": _num(r.get("quantidade")),
                "e": codigo_eh_estocado(r.get("produto_codigo")),
            })
    else:
        for p in posicoes_padrao():
            pal.append({"id": None, "rot": p["rot"], "x": p["x"] / 100, "z": p["z"] / 100, "c": "", "n": "", "q": 0.0, "e": False})

    # Fileiras: agrupa os Z (a 10 cm), do fundo (maior Z) para a frente
    zs = sorted({round(p["z"] * 10) for p in pal}, reverse=True)
    fileira_de = {z: i + 1 for i, z in enumerate(zs)}
    for p in pal:
        p["f"] = fileira_de[round(p["z"] * 10)]

    catalogo: dict[str, str] = {}
    catalogo_est: set[tuple[str, str]] = set()
    for p in pal:
        if not p["c"].strip():
            continue
        if p["e"]:  # estocado: um item por cooperado (o código se repete entre cooperados)
            catalogo_est.add((p["c"], p["n"]))
        else:
            catalogo.setdefault(p["c"], p["n"])
    return {
        "padrao": padrao,
        "w": LARGURA / 100, "d": PROFUNDIDADE / 100, "h": PE_DIREITO / 100, "esp": ESPESSURA / 100,
        "aberturas": [{"tipo": t, "x0": a / 100, "x1": b / 100, "h": h / 100} for t, a, b, h in ABERTURAS],
        "palete": {"x": PALETE_X / 100, "z": PALETE_Z / 100, "h": PALETE_H / 100},
        "bag": {"x": BAG_X / 100, "z": BAG_Z / 100, "h": BAG_H / 100},
        "corredor": CORREDOR_MANOBRA / 100,
        "fileiras": len(zs),
        "pal": pal,
        "catalogo": catalogo_da_cena(catalogo, catalogo_est),
        "avisos": (["barracao_enderecos está vazia ou não pôde ser lida; o barracão mostra o layout padrão, com todos os paletes livres."]
                   if padrao else []),
    }
