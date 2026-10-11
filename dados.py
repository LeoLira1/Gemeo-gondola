"""Leitura do Turso (somente leitura) e montagem do JSON que vai para a cena 3D.

O token só existe aqui, no servidor Python: a cena recebe um JSON de dados já
prontos e nada mais.
"""

from __future__ import annotations

import math
import random
from typing import Any

import requests

import galpao as g
import barracao as br
import loja as lj

TIMEOUT_S = 20

SQL_RACKS = (
    "SELECT posicao, ordem, produto_codigo, produto_nome, quantidade "
    "FROM galpao_racks ORDER BY posicao, ordem"
)
SQL_POSICOES = "SELECT numero, pos_x, pos_z FROM galpao_posicoes"
SQL_MESTRE = "SELECT codigo, produto, qtd_sistema FROM estoque_mestre LIMIT 5000"
SQL_MAPA = "SELECT produto_id, codigo FROM mapa_produtos WHERE codigo IS NOT NULL"
SQL_MAPA_COD = "SELECT produto_id, codigo FROM mapa_produtos_codigos WHERE codigo IS NOT NULL"
SQL_ENDERECADO = (
    "SELECT produto_codigo, SUM(quantidade) AS enderecado "
    "FROM estoque_localizado GROUP BY produto_codigo"
)


class TursoErro(Exception):
    pass


def _valor(celula: dict[str, Any]) -> Any:
    tipo = celula.get("type")
    if tipo == "null":
        return None
    v = celula.get("value")
    if tipo == "integer":
        return int(v)
    if tipo == "float":
        return float(v)
    return v  # text (blob não é usado)


def consultar(url: str, token: str, sqls: list[str]) -> list[list[dict[str, Any]] | None]:
    """Executa várias consultas numa ida só (Hrana sobre HTTP, /v2/pipeline).

    Devolve, para cada SQL, a lista de linhas como dicts — ou None se aquela
    consulta falhou (ex.: tabela do mapa que nunca foi criada). Falha de
    conexão ou de autenticação levanta TursoErro.
    """
    base = url.strip().replace("libsql://", "https://", 1).rstrip("/")
    corpo = {
        "requests": [{"type": "execute", "stmt": {"sql": s}} for s in sqls]
        + [{"type": "close"}]
    }
    try:
        resp = requests.post(
            f"{base}/v2/pipeline",
            json=corpo,
            headers={"Authorization": f"Bearer {token.strip()}"},
            timeout=TIMEOUT_S,
        )
    except requests.RequestException as e:
        raise TursoErro(f"sem conexão com o Turso ({type(e).__name__})") from None
    if resp.status_code in (401, 403):
        raise TursoErro("Turso recusou o token (TURSO_TOKEN inválido ou expirado)")
    if resp.status_code != 200:
        raise TursoErro(f"Turso respondeu HTTP {resp.status_code}")

    saida: list[list[dict[str, Any]] | None] = []
    for item in resp.json().get("results", [])[: len(sqls)]:
        if item.get("type") != "ok":
            saida.append(None)
            continue
        res = item["response"]["result"]
        cols = [c["name"] for c in res["cols"]]
        saida.append([dict(zip(cols, map(_valor, row))) for row in res["rows"]])
    while len(saida) < len(sqls):
        saida.append(None)
    return saida


# ── Montagem ────────────────────────────────────────────────────────────────


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def montar(
    racks: list[dict[str, Any]],
    mestre: list[dict[str, Any]],
    vinculos: dict[str, str],
    enderecado_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cruza as leituras e devolve o JSON da cena (sem segredo nenhum)."""
    pilhas: dict[int, list[dict[str, Any]]] = {}
    for r in racks:
        pos = r.get("posicao")
        if pos not in g.POSICAO_POR_NUMERO:  # linha órfã: fora da planta
            continue
        pilhas.setdefault(pos, []).append(
            {
                "o": int(r.get("ordem") or 1),
                "c": r.get("produto_codigo") or "",
                "nome": r.get("produto_nome") or "",
                "q": _num(r.get("quantidade")),
            }
        )

    sistema: dict[str, float] = {}
    nome_mestre: dict[str, str] = {}
    for m in mestre:
        c = g.normalizar_codigo(m.get("codigo"))
        if c is None:
            continue
        sistema[c] = _num(m.get("qtd_sistema"))
        nome_mestre[c] = m.get("produto") or ""

    enderecado: dict[str, float] = {}
    for e in enderecado_rows:
        c = g.normalizar_codigo(e.get("produto_codigo"))
        if c is not None:
            enderecado[c] = _num(e.get("enderecado"))

    codigos_com_rack = {r["c"] for pilha in pilhas.values() for r in pilha if r["c"].strip()}
    grupos = g.grupos_de_codigos(codigos_com_rack, vinculos, nome_mestre)
    saldos = g.montar_saldos(codigos_com_rack, grupos, sistema, enderecado)

    # Nome: o do estoque_mestre quando existe, senão o gravado no rack.
    catalogo: dict[str, str] = {}
    for pilha in pilhas.values():
        for r in pilha:
            if not r["c"].strip():
                continue
            nome = nome_mestre.get(g.normalizar_codigo(r["c"]) or "") or r["nome"]
            catalogo.setdefault(r["c"], nome)
            if not r["nome"]:
                r["nome"] = nome
    for pilha in pilhas.values():
        for r in pilha:
            r["nome"] = catalogo.get(r["c"], r["nome"])

    divergencia = {
        cod: {
            "t": "falta" if s.falta else "sobra",
            "sis": s.qtd_sistema,
            "end": s.enderecado,
            "cods": list(s.codigos_somados) if len(s.codigos_somados) > 1 else [],
        }
        for cod, s in saldos.items()
        if s.falta or s.sobra
    }

    return {
        "posicoes": [
            {
                "n": p.numero,
                "r": p.rua.numero,
                "p": p.parte,
                "x": round(p.x, 4),
                "z": round(p.z, 4),
                "sx": p.tamanho_x,
                "sz": p.tamanho_z,
            }
            for p in g.POSICOES
        ],
        "ruas": [
            {"n": r.numero, "p": r.parte, "eixo": r.eixo, "de": r.primeiro_numero, "ate": r.ultimo_numero, "lado": r.lado_corredor}
            for r in g.RUAS
        ],
        "geo": {
            "comp": g.COMPRIMENTO_RACK,
            "larg": g.LARGURA_RACK,
            "alt": g.ALTURA_NIVEL,
            "passoNivel": g.PASSO_NIVEL,
            "niveisMax": g.NIVEIS_MAX,
        },
        "pilhas": {str(n): sorted(p, key=lambda r: r["o"]) for n, p in pilhas.items()},
        "divergencia": divergencia,
        "catalogo": [{"c": c, "n": n} for c, n in sorted(catalogo.items())],
    }


def ler_turso(url: str, token: str) -> dict[str, Any]:
    racks, posicoes, mestre, mapa, mapa_cod, end = consultar(
        url, token, [SQL_RACKS, SQL_POSICOES, SQL_MESTRE, SQL_MAPA, SQL_MAPA_COD, SQL_ENDERECADO]
    )
    if racks is None or mestre is None or end is None:
        raise TursoErro("não consegui ler galpao_racks / estoque_mestre / estoque_localizado")

    vinculos: dict[str, str] = {}
    for tabela in (mapa, mapa_cod):  # tabela ausente: segue só com o nome
        for row in tabela or []:
            c = g.normalizar_codigo(row.get("codigo"))
            pid = str(row.get("produto_id") if row.get("produto_id") is not None else "").strip()
            if c and pid:
                vinculos[c] = pid

    dados = montar(racks, mestre, vinculos, end)
    dados["avisos"] = _avisos_planta(posicoes)
    return dados


def _avisos_planta(linhas: list[dict[str, Any]] | None) -> list[str]:
    """A planta é a do código (como no Gondolas); a tabela é só o espelho."""
    if linhas is None:
        return ["galpao_posicoes não pôde ser lida; usando a planta do código."]
    por_num = {r["numero"]: r for r in linhas}
    if len(por_num) != g.TOTAL_POSICOES:
        return [f"galpao_posicoes tem {len(por_num)} linhas (esperado {g.TOTAL_POSICOES}); a planta usada é a do código."]
    for p in g.POSICOES:
        r = por_num.get(p.numero)
        if r is None or abs(_num(r["pos_x"]) - p.x) > 0.01 or abs(_num(r["pos_z"]) - p.z) > 0.01:
            return ["galpao_posicoes difere da planta do código; a planta usada é a do código."]
    return []


# ── Dados de exemplo (sem Turso) ────────────────────────────────────────────

_PRODUTOS_DEMO = [
    ("254185", "HERBICIDA BORAL 500 SC 20L"),
    ("US254185", "HERBICIDA BORAL 500 SC 20L"),
    ("100237191", "HERBICIDA ULTIMATO 5L"),
    ("300112", "FUNGICIDA OPERA ULTRA 5L"),
    ("300245", "INSETICIDA ENGEO PLENO S 1L"),
    ("410077", "ADUBO FOLIAR NUTRI-K 20L"),
    ("410078", "ADUBO FOLIAR NUTRI-ZN 20L"),
    ("520310", "OLEO MINERAL ASSIST 20L"),
    ("520311", "ESPALHANTE ADESIVO LI 700 5L"),
    ("610001", "HERBICIDA GLIFOSATO ATANOR 20L"),
    ("610002", "HERBICIDA 2,4-D AMINA 20L"),
    ("720450", "FUNGICIDA PRIORI XTRA 5L"),
    ("720451", "FUNGICIDA AMISTAR TOP 5L"),
    ("830900", "INSETICIDA CRUISER 350 FS 5L"),
    ("830901", "INSETICIDA FASTAC DUO 5L"),
    ("940020", "SAL MINERAL BOVINO 25KG"),
]


def dados_exemplo() -> dict[str, Any]:
    """Galpão fictício, determinístico, só para ver o mapa sem o banco."""
    rnd = random.Random(129)
    racks: list[dict[str, Any]] = []
    for p in g.POSICOES:
        if rnd.random() < 0.22:
            continue  # vaga livre
        for ordem in range(1, rnd.choice([1, 1, 2, 2, 3, 4]) + 1):
            cod, nome = rnd.choice(_PRODUTOS_DEMO)
            racks.append(
                {"posicao": p.numero, "ordem": ordem, "produto_codigo": cod,
                 "produto_nome": nome, "quantidade": rnd.choice([20, 24, 30, 40, 48, 60, 90])}
            )
    totais: dict[str, float] = {}
    for r in racks:
        totais[r["produto_codigo"]] = totais.get(r["produto_codigo"], 0) + r["quantidade"]
    mestre = []
    for cod, nome in _PRODUTOS_DEMO:
        end = totais.get(cod, 0)
        # alguns fecham, alguns faltam, alguns sobram
        fator = {"254185": 1.0, "300112": 1.4, "410077": 0.7}.get(cod, 1.0)
        if cod == "254185":  # irmão US254185 soma junto
            end = totais.get("254185", 0) + totais.get("US254185", 0)
            mestre.append({"codigo": cod, "produto": nome, "qtd_sistema": end})
            continue
        if cod == "US254185":
            mestre.append({"codigo": cod, "produto": nome, "qtd_sistema": 0})
            continue
        mestre.append({"codigo": cod, "produto": nome, "qtd_sistema": round(end * fator)})
    enderecado = [{"produto_codigo": c, "enderecado": q} for c, q in totais.items()]
    dados = montar(racks, mestre, {}, enderecado)
    dados["avisos"] = []
    return dados


# ── Loja (gôndolas e estantes) ──────────────────────────────────────────────

SQL_GONDOLAS = (
    "SELECT DISTINCT produto_codigo, produto_nome, gondola_num, andar, pos_x, pos_z "
    "FROM gondola_layout ORDER BY produto_nome"
)
SQL_ESTANTES = (
    "SELECT DISTINCT produto_codigo, produto_nome, estante_num, nivel FROM estante_layout "
    f"WHERE estante_num NOT IN ({', '.join(map(str, lj.ESTANTES_REMOVIDAS))}) "
    f"AND NOT (estante_num = {lj.NELLORE} AND nivel = 0) ORDER BY produto_nome"
)
SQL_QTD_LOJA = (
    "SELECT produto_codigo, local_tipo, local_num, face_ou_coluna, andar_ou_nivel, quantidade "
    "FROM estoque_localizado WHERE local_tipo IN ('gondola', 'estante')"
)


def ler_loja(url: str, token: str) -> dict[str, Any]:
    gond, est, qtd = consultar(url, token, [SQL_GONDOLAS, SQL_ESTANTES, SQL_QTD_LOJA])
    if gond is None or est is None:
        raise TursoErro("não consegui ler gondola_layout / estante_layout")
    dados = lj.montar(gond, est, qtd or [])
    dados["avisos"] = [] if qtd is not None else ["estoque_localizado não pôde ser lida; as quantidades não aparecem."]
    return dados


def loja_exemplo() -> dict[str, Any]:
    """Loja fictícia, determinística, só para ver o mapa sem o banco."""
    rnd = random.Random(21)
    gond, est, qtd = [], [], []
    for it in lj.ITENS:
        if it["kind"] == "balcao":
            continue
        for _ in range(rnd.randint(3, 9)):
            cod, nome = rnd.choice(_PRODUTOS_DEMO)
            q = rnd.choice([6, 10, 12, 20, 24, 36])
            if it["tipo"] == "gondola":
                face, andar = rnd.randint(1, 6), rnd.randint(0, 2)
                ang = math.radians(90 - 60 * (face - 1))
                gond.append({"produto_codigo": cod, "produto_nome": nome, "gondola_num": it["n"],
                             "andar": andar, "pos_x": math.cos(ang), "pos_z": math.sin(ang)})
                qtd.append({"produto_codigo": cod, "local_tipo": "gondola", "local_num": it["n"],
                            "face_ou_coluna": face, "andar_ou_nivel": andar, "quantidade": q})
            else:
                nivel = rnd.randint(0, lj.niveis_produto(it["n"]) - 1)
                num = it["n"] + (rnd.randint(0, 5) if it["kind"] == "parede" else 0)
                est.append({"produto_codigo": cod, "produto_nome": nome, "estante_num": num, "nivel": nivel})
                qtd.append({"produto_codigo": cod, "local_tipo": "estante", "local_num": num,
                            "face_ou_coluna": 0, "andar_ou_nivel": nivel, "quantidade": q})
    dados = lj.montar(gond, est, qtd)
    dados["avisos"] = []
    return dados


# ── Barracão ────────────────────────────────────────────────────────────────

SQL_BARRACAO = (
    "SELECT id, rotulo, pos_x, pos_z, produto_codigo, produto_nome, quantidade "
    "FROM barracao_enderecos ORDER BY id"
)


def ler_barracao(url: str, token: str) -> dict[str, Any]:
    """Barracão: um palete por linha de barracao_enderecos. Tabela ausente/vazia → layout padrão."""
    (linhas,) = consultar(url, token, [SQL_BARRACAO])
    return br.montar(linhas)


def barracao_exemplo() -> dict[str, Any]:
    """Barracão fictício, determinístico, só para ver o mapa sem o banco."""
    rnd = random.Random(35)
    linhas = []
    for i, p in enumerate(br.posicoes_padrao()):
        cod, nome = ("", "") if rnd.random() < 0.3 else rnd.choice(_PRODUTOS_DEMO)
        linhas.append({"id": i + 1, "rotulo": p["rot"], "pos_x": p["x"], "pos_z": p["z"],
                       "produto_codigo": cod, "produto_nome": nome, "quantidade": rnd.choice([1, 1, 2, 4]) if cod else 0})
    return br.montar(linhas)
