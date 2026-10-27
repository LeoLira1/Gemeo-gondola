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
import estocados as es

TIMEOUT_S = 20

SQL_RACKS = (
    "SELECT posicao, ordem, produto_codigo, produto_nome, quantidade "
    "FROM galpao_racks ORDER BY posicao, ordem"
)
# Rack misto (até 5 produtos no mesmo palete, no Gondolas): os produtos ALÉM do primeiro, com a posição
# e o nível do rack que os leva. Consulta à parte: num banco sem a tabela ela volta None e o galpão
# segue só com os racks.
SQL_ITENS = (
    "SELECT r.posicao, r.ordem, i.produto_codigo, i.produto_nome, i.quantidade "
    "FROM galpao_rack_itens i JOIN galpao_racks r ON r.rack_uuid = i.rack_uuid "
    "ORDER BY r.posicao, r.ordem, i.id"
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
    itens: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cruza as leituras e devolve o JSON da cena (sem segredo nenhum).

    `itens` são os produtos extras dos racks mistos: entram no rack como `it` (lista de
    {c, nome, q}), e contam para saldo, nome e busca como qualquer produto de rack.
    """
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
                "e": es.codigo_eh_estocado(r.get("produto_codigo")),
            }
        )

    por_nivel = {(pos, r["o"]): r for pos, pilha in pilhas.items() for r in pilha}
    for i in itens or []:
        rack = por_nivel.get((i.get("posicao"), int(i.get("ordem") or 1)))
        if rack is None:  # item de rack que não está na leitura (órfão, fora da planta)
            continue
        rack.setdefault("it", []).append(
            {"c": i.get("produto_codigo") or "", "nome": i.get("produto_nome") or "", "q": _num(i.get("quantidade"))}
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

    # "EST:" (material de cooperado) fica FORA do saldo: não entra em grupos, saldos nem divergência.
    codigos_com_rack = {r["c"] for pilha in pilhas.values() for r in pilha if r["c"].strip() and not r["e"]}
    codigos_com_rack |= {i["c"] for r in _racks(pilhas) for i in r.get("it", []) if i["c"].strip()}
    grupos = g.grupos_de_codigos(codigos_com_rack, vinculos, nome_mestre)
    saldos = g.montar_saldos(codigos_com_rack, grupos, sistema, enderecado)

    # Nome: o do estoque_mestre quando existe, senão o gravado no rack. Estocado (EST:) NUNCA é renomeado:
    # dois cooperados com o mesmo produto têm o mesmo código, e o nome é o que liga o palete ao item.
    catalogo: dict[str, str] = {}
    catalogo_est: set[tuple[str, str]] = set()
    for pilha in pilhas.values():
        for r in pilha:
            if not r["c"].strip():
                continue
            if r["e"]:
                catalogo_est.add((r["c"], r["nome"]))
                continue
            nome = nome_mestre.get(g.normalizar_codigo(r["c"]) or "") or r["nome"]
            catalogo.setdefault(r["c"], nome)
            if not r["nome"]:
                r["nome"] = nome
    for i in (i for r in _racks(pilhas) for i in r.get("it", [])):
        if i["c"].strip():
            catalogo.setdefault(i["c"], nome_mestre.get(g.normalizar_codigo(i["c"]) or "") or i["nome"])
    for pilha in pilhas.values():
        for r in pilha:
            if not r["e"]:
                r["nome"] = catalogo.get(r["c"], r["nome"])
            for i in r.get("it", []):
                i["nome"] = catalogo.get(i["c"], i["nome"])

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
            {"n": r.numero, "p": r.parte, "eixo": r.eixo, "de": r.primeiro_numero, "ate": r.ultimo_numero, "lado": r.lado_corredor,
             "gaiola": r.rack_atravessado, "centro": r.centro}
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
        "catalogo": es.catalogo_da_cena(catalogo, catalogo_est),
        "escada": g.escada(),
        "lavaolhos": g.lava_olhos(),
        "mesa": g.mesa(),
    }


def _racks(pilhas: dict[Any, list[dict[str, Any]]]):
    return (r for pilha in pilhas.values() for r in pilha)


def _montar_galpao_de(racks, posicoes, mestre, mapa, mapa_cod, end, itens=None) -> dict[str, Any]:
    if racks is None or mestre is None or end is None:
        raise TursoErro("não consegui ler galpao_racks / estoque_mestre / estoque_localizado")

    vinculos: dict[str, str] = {}
    for tabela in (mapa, mapa_cod):  # tabela ausente: segue só com o nome
        for row in tabela or []:
            c = g.normalizar_codigo(row.get("codigo"))
            pid = str(row.get("produto_id") if row.get("produto_id") is not None else "").strip()
            if c and pid:
                vinculos[c] = pid

    dados = montar(racks, mestre, vinculos, end, itens)
    dados["avisos"] = _avisos_planta(posicoes)
    return dados


def ler_turso(url: str, token: str) -> dict[str, Any]:
    return _montar_galpao_de(
        *consultar(url, token, [SQL_RACKS, SQL_POSICOES, SQL_MESTRE, SQL_MAPA, SQL_MAPA_COD, SQL_ENDERECADO, SQL_ITENS])
    )


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
# Cores por categoria do Gondolas (TursoService.categoriaCores): o cor_hex que vai para o layout.
_CORES_DEMO = ["#2e7d4f", "#2c5fb0", "#6b4a2b", "#d9b46a", "#e87722", "#8b1a1a", "#c8a000", "#4a4a8a"]


_TERCEIROS_DEMO = [
    {"razao_social": "MARIA SOUZA", "descricao": "ADUBO FOLIAR NUTRI-K 20L", "codigo": "410077", "armazem": "01", "saldo": "12"},
    {"razao_social": "JOAO SILVA", "descricao": "HERBICIDA BORAL 500 SC 20L", "codigo": "254185", "armazem": "01", "saldo": "30"},
    {"razao_social": "JOÃO SILVA", "descricao": "FUNGICIDA OPERA ULTRA 5L", "codigo": "300112", "armazem": "02", "saldo": "8"},
    {"razao_social": "FAZENDA BOA VISTA", "descricao": "SAL MINERAL BOVINO 25KG", "codigo": "", "armazem": "01", "saldo": "40"},
]


def _estocados_demo_racks(racks: list[dict[str, Any]]) -> None:
    """Dois paletes de estocado em vagas livres do galpão de exemplo (um com 2 níveis)."""
    ocupadas = {r["posicao"] for r in racks}
    livres = [p.numero for p in g.POSICOES if p.numero not in ocupadas][:2]
    for pos, linha in zip(livres, _TERCEIROS_DEMO[:2]):
        i = es.item_de_linha(linha)
        racks.append({"posicao": pos, "ordem": 1, "produto_codigo": i.codigo_do_palete,
                      "produto_nome": i.nome_do_palete, "quantidade": i.saldo})


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
    _estocados_demo_racks(racks)
    # Um rack misto: o primeiro rack de loja ganha mais dois produtos no mesmo palete.
    base = next(r for r in racks if not es.codigo_eh_estocado(r["produto_codigo"]))
    outros = [c for c in _PRODUTOS_DEMO if c[0] in ("300245", "410078") and c[0] != base["produto_codigo"]][:2]
    itens = [{"posicao": base["posicao"], "ordem": base["ordem"], "produto_codigo": c, "produto_nome": n,
              "quantidade": q} for (c, n), q in zip(outros, (6, 4))]
    totais: dict[str, float] = {}
    for r in [*racks, *itens]:
        if es.codigo_eh_estocado(r["produto_codigo"]):
            continue  # fora do saldo
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
    dados = montar(racks, mestre, {}, enderecado, itens)
    dados["avisos"] = []
    return dados


# ── Loja (gôndolas e estantes) ──────────────────────────────────────────────

SQL_GONDOLAS = (
    "SELECT DISTINCT produto_codigo, produto_nome, gondola_num, andar, pos_x, pos_z, cor_hex "
    "FROM gondola_layout ORDER BY produto_nome"
)
SQL_ESTANTES = (
    "SELECT DISTINCT produto_codigo, produto_nome, estante_num, nivel, coluna, slot, cor_hex FROM estante_layout "
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
                raio = lj.GONDOLA_PRATELEIRAS[andar][0] * 0.7      # na escala da cena de detalhe do app
                gond.append({"produto_codigo": cod, "produto_nome": nome, "gondola_num": it["n"],
                             "andar": andar, "pos_x": raio * math.cos(ang), "pos_z": raio * math.sin(ang),
                             "cor_hex": rnd.choice(_CORES_DEMO)})
                qtd.append({"produto_codigo": cod, "local_tipo": "gondola", "local_num": it["n"],
                            "face_ou_coluna": face, "andar_ou_nivel": andar, "quantidade": q})
            else:
                nivel = rnd.randint(0, lj.niveis_produto(it["n"]) - 1)
                num = it["n"] + (rnd.randint(0, 5) if it["kind"] == "parede" else 0)
                col = rnd.randint(0, lj.PRODUTOS_POR_ESPACO_ILHA - 1) if it["kind"] == "ilha" else 0
                if it["kind"] == "madeira":
                    col = rnd.randint(0, 5)                          # 6 produtos por degrau
                elif it["kind"] not in ("ilha", "mostruario"):
                    col = rnd.randint(0, 2)
                est.append({"produto_codigo": cod, "produto_nome": nome, "estante_num": num, "nivel": nivel,
                            "coluna": col, "slot": rnd.randint(0, 3), "cor_hex": rnd.choice(_CORES_DEMO)})
                qtd.append({"produto_codigo": cod, "local_tipo": "estante", "local_num": num,
                            "face_ou_coluna": col, "andar_ou_nivel": nivel, "quantidade": q})
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
    i = es.item_de_linha(_TERCEIROS_DEMO[2])  # um estocado no primeiro palete livre
    for l in linhas:
        if not l["produto_codigo"]:
            l.update(produto_codigo=i.codigo_do_palete, produto_nome=i.nome_do_palete, quantidade=i.saldo)
            break
    return br.montar(linhas)


# ── Busca global: um índice com o produto de cada local, nos três mapas ─────


def indice_global(galpao: dict[str, Any], loja: dict[str, Any], barracao: dict[str, Any]) -> list[dict[str, Any]]:
    """Uma linha por produto em cada local: {c: código, n: nome, a: mapa, w: local}.

    É o que deixa a busca de qualquer aba achar o produto em TODOS os mapas.
    """
    out: list[dict[str, Any]] = []
    for pos, pilha in galpao["pilhas"].items():
        for r in pilha:
            for p in [r, *r.get("it", [])]:
                if p["c"].strip():
                    out.append({"c": p["c"], "n": p["nome"], "a": "galpao", "w": pos})
    for it in loja["itens"]:
        for p in it["prod"]:
            if p["c"].strip():
                out.append({"c": p["c"], "n": p["n"], "a": "loja", "w": it["rot"]})
    for p in barracao["pal"]:
        if p["c"].strip():
            out.append({"c": p["c"], "n": p["n"], "a": "barracao", "w": p["rot"]})
    return out


def estocados_da_cena(linhas, galpao: dict[str, Any], barracao: dict[str, Any]) -> dict[str, Any]:
    """Lista de materiais_terceiros + endereço de cada item (liga o palete pelo nome "PRODUTO · COOPERADO")."""
    racks = [(int(n), r) for n, pilha in galpao["pilhas"].items() for r in pilha]
    return es.para_cena(linhas, racks, barracao["pal"])


def resumo_galpao(galpao: dict[str, Any]) -> str:
    """"38 livres · 30 estocados · 61 loja"; vagas = posições × níveis (138 × 4 = 552)."""
    total = len(galpao["posicoes"]) * galpao["geo"]["niveisMax"]
    return es.resumo_ocupacao(total, (r["c"] for pilha in galpao["pilhas"].values() for r in pilha))


def ler_tudo(url: str, token: str) -> dict[str, Any]:
    """Galpão, loja e barracão numa ida só ao Turso. Um mapa que falha vira dados de exemplo
    (anotado em `erros`), sem derrubar os outros."""
    res = consultar(url, token, [SQL_RACKS, SQL_POSICOES, SQL_MESTRE, SQL_MAPA, SQL_MAPA_COD, SQL_ENDERECADO,
                                 SQL_GONDOLAS, SQL_ESTANTES, SQL_QTD_LOJA, SQL_BARRACAO, es.SQL_ESTOCADOS, SQL_ITENS])
    erros: dict[str, str] = {}
    try:
        galpao = _montar_galpao_de(*res[:6], itens=res[11])
    except TursoErro as e:
        galpao, erros["galpao"] = dados_exemplo(), str(e)
    gond, est, qtd, barr, terc = res[6:11]
    if gond is None or est is None:
        loja, erros["loja"] = loja_exemplo(), "não consegui ler gondola_layout / estante_layout"
    else:
        loja = lj.montar(gond, est, qtd or [])
        loja["avisos"] = [] if qtd is not None else ["estoque_localizado não pôde ser lida; as quantidades da loja não aparecem."]
    barracao = br.montar(barr)
    return {"galpao": galpao, "loja": loja, "barracao": barracao, "erros": erros,
            "estocados": estocados_da_cena(terc, galpao, barracao)}


def tudo_exemplo() -> dict[str, Any]:
    galpao, barracao = dados_exemplo(), barracao_exemplo()
    return {"galpao": galpao, "loja": loja_exemplo(), "barracao": barracao, "erros": {},
            "estocados": estocados_da_cena(_TERCEIROS_DEMO, galpao, barracao)}


# ── Ocupação em porcentagem (indicadores do topo da página) ─────────────────


def percentual(parte: float, todo: float) -> int:
    """Porcentagem inteira (arredonda metade para cima); 0 quando não há total."""
    return int(100 * parte / todo + 0.5) if todo else 0


def ocupacao_galpao(g_: dict[str, Any]) -> dict[int, dict[str, int]]:
    """Capacidade usada de CADA parte do galpão, separadas: racks ÷ (posições da parte × níveis).

    Devolve {parte: {"racks", "capacidade" (em racks), "pct"}}.
    """
    niveis = g_["geo"]["niveisMax"]
    parte_de = {p["n"]: p["p"] for p in g_["posicoes"]}
    posicoes: dict[int, int] = {}
    for parte in parte_de.values():
        posicoes[parte] = posicoes.get(parte, 0) + 1
    racks: dict[int, int] = {parte: 0 for parte in posicoes}
    for n, pilha in g_["pilhas"].items():
        parte = parte_de.get(int(n))
        if parte is not None:
            racks[parte] += len(pilha)
    return {
        parte: {"racks": racks[parte], "capacidade": posicoes[parte] * niveis,
                "pct": percentual(racks[parte], posicoes[parte] * niveis)}
        for parte in sorted(posicoes)
    }


def ocupacao_barracao(b_: dict[str, Any]) -> int:
    return percentual(sum(1 for p in b_["pal"] if p["c"].strip()), len(b_["pal"]))


def ocupacao_loja(l_: dict[str, Any]) -> dict[str, int]:
    """Faixas de endereço da loja (face × andar da gôndola, nível da estante) com ao menos um produto."""
    total = sum(i["faixas"] for i in l_["itens"])
    ocupadas = sum(i["ocupadas"] for i in l_["itens"])
    return {"ocupadas": ocupadas, "total": total, "pct": percentual(ocupadas, total)}


def capacidades(tudo: dict[str, Any]) -> list[dict[str, Any]]:
    """A capacidade de cada área, independente das outras e em relação às SUAS vagas:
    Galpão 1, Galpão 2, Barracão e Loja. Cada item: {nome, pct, dica, cor}."""
    out = []
    for parte, o in ocupacao_galpao(tudo["galpao"]).items():
        out.append({"nome": f"Galpão {parte}", "pct": o["pct"], "cor": "#d8d4ca",
                    "dica": f"Galpão {parte}: {o['racks']} racks de {o['capacidade']} (posições × {tudo['galpao']['geo']['niveisMax']} níveis)"})
    b = tudo["barracao"]["pal"]
    cheios = sum(1 for p in b if p["c"].strip())
    out.append({"nome": "Barracão", "pct": percentual(cheios, len(b)), "cor": "#c99d66",
                "dica": f"Barracão: {cheios} paletes com bag de {len(b)}"})
    lj_ = ocupacao_loja(tudo["loja"])
    out.append({"nome": "Loja", "pct": lj_["pct"], "cor": "#4caf50",
                "dica": f"Loja: {lj_['ocupadas']} de {lj_['total']} faixas de endereço (gôndola: face × andar; estante: nível)"})
    return out
