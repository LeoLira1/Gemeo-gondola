import math

import galpao as g
import dados as dd


def test_planta_138_posicoes_85_53():
    assert g.TOTAL_POSICOES == 138
    assert sorted(p.numero for p in g.POSICOES) == list(range(1, 139))
    assert sum(1 for p in g.POSICOES if p.parte == 1) == 85
    assert sum(1 for p in g.POSICOES if p.parte == 2) == 53          # 44 nas fileiras + 9 gaiolas
    assert len(g.RUAS) == 15
    assert {r.numero for r in g.RUAS if r.parte == 2} == {9, 10, 11, 12, 13, 14, 15}
    assert min(p.numero for p in g.POSICOES if p.parte == 2) == 86


def test_gaiolas_no_fim_de_cada_corredor_da_parte_2():
    fileira = {r.numero: r for r in g.RUAS if r.parte == 2 and not r.rack_atravessado}
    fundo = min(p.z for p in g.POSICOES if p.rua.numero == 12)       # a ponta do 129 / 86
    for rua, (esq, dir_), primeiro in [(13, (12, 11), 130), (14, (11, 10), 133), (15, (10, 9), 136)]:
        ps = sorted((p for p in g.POSICOES if p.rua.numero == rua), key=lambda p: p.x)
        assert [p.numero for p in ps] == [primeiro, primeiro + 1, primeiro + 2]   # da esquerda para a direita
        borda_esq = fileira[esq].coord_fixa + g.LARGURA_RACK / 2
        borda_dir = fileira[dir_].coord_fixa - g.LARGURA_RACK / 2
        for p in ps:
            assert p.parte == 2 and p.tamanho_x == g.LARGURA_RACK and p.tamanho_z == g.COMPRIMENTO_RACK
            assert borda_esq < p.x - p.tamanho_x / 2 and p.x + p.tamanho_x / 2 < borda_dir   # cabe no corredor
            assert math.isclose(p.z, fundo, abs_tol=1e-9)
        assert math.isclose(ps[1].x - ps[0].x, g.PASSO_GAIOLA, abs_tol=1e-9)


def _por_rua(numero_rua):
    return sorted((p for p in g.POSICOES if p.rua.numero == numero_rua), key=lambda p: p.numero)


def test_serpentina_da_parte_2_e_perimetro_da_parte_1():
    # 96→97, 107→108, 118→119 ficam lado a lado na virada da serpentina
    for fim, ini in [(96, 97), (107, 108), (118, 119)]:
        a, b = g.POSICAO_POR_NUMERO[fim], g.POSICAO_POR_NUMERO[ini]
        assert abs(a.z - b.z) < 1e-9
        assert math.isclose(abs(a.x - b.x), 4.45, abs_tol=1e-6)
    # 86 no topo (Z negativo), 96 embaixo; 97 embaixo, 107 em cima
    assert g.POSICAO_POR_NUMERO[86].z < g.POSICAO_POR_NUMERO[96].z
    assert g.POSICAO_POR_NUMERO[97].z > g.POSICAO_POR_NUMERO[107].z
    # Rua 1: nº 1 em Z positivo, 14 em Z negativo (topo)
    assert g.POSICAO_POR_NUMERO[1].z > g.POSICAO_POR_NUMERO[14].z
    # Rua 2 atravessa o topo: 15 em X positivo, 25 em X negativo
    assert g.POSICAO_POR_NUMERO[15].x > g.POSICAO_POR_NUMERO[25].x
    # pares costas com costas: 1,05 m entre ruas 4/5 e 6/7
    assert math.isclose(g.RUAS[4].coord_fixa - g.RUAS[3].coord_fixa, 1.05, abs_tol=1e-9)
    assert math.isclose(g.RUAS[6].coord_fixa - g.RUAS[5].coord_fixa, 1.05, abs_tol=1e-9)


def test_chave_nome_e_codigos_irmaos():
    assert g.chave_nome_produto("  Óleo   Mineral ") == "OLEO MINERAL"
    grupos = g.grupos_de_codigos(
        ["254185", "US254185", "X1"],
        produto_id_por_codigo={},
        nome_por_codigo={"254185": "BORAL 20L", "US254185": "boral  20l", "X1": "OUTRO"},
    )
    assert grupos["254185"] == {"254185", "US254185"}
    assert grupos["X1"] == {"X1"}
    # o cadastro manda mais que o nome: irmão vinculado a outro produto fica de fora
    grupos = g.grupos_de_codigos(
        ["A", "B"],
        produto_id_por_codigo={"B": "9"},
        nome_por_codigo={"A": "MESMO NOME", "B": "MESMO NOME"},
    )
    assert grupos["A"] == {"A"} and grupos["B"] == {"B"}


def test_saldo_soma_todos_os_codigos():
    grupos = {"254185": {"254185", "US254185"}}
    s = g.montar_saldos(
        ["254185"], grupos,
        sistema_por_codigo={"254185": 171.0, "US254185": 388.0},
        enderecado_por_codigo={"254185": 100.0, "US254185": 300.0},
    )["254185"]
    assert (s.qtd_sistema, s.enderecado) == (559.0, 400.0)
    assert s.falta and not s.sobra
    # sem linha no estoque_mestre → sem saldo (não inventa falta)
    assert g.montar_saldos(["Z"], {}, {}, {"Z": 5.0}) == {}
    # fecha dentro da tolerância
    fecha = g.montar_saldos(["A"], {}, {"A": 10.0}, {"A": 10.0005})["A"]
    assert not fecha.falta and not fecha.sobra


def test_montar_json_sem_segredo_e_com_divergencia():
    racks = [
        {"posicao": 86, "ordem": 1, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 30},
        {"posicao": 86, "ordem": 2, "produto_codigo": "B", "produto_nome": "", "quantidade": 10},
        {"posicao": 999, "ordem": 1, "produto_codigo": "A", "produto_nome": "orfa", "quantidade": 1},
    ]
    mestre = [
        {"codigo": "A", "produto": "PROD A", "qtd_sistema": 100},   # 30 endereçado → falta
        {"codigo": "B", "produto": "PROD B", "qtd_sistema": 5},     # 10 endereçado → sobra
    ]
    out = dd.montar(racks, mestre, {}, [{"produto_codigo": "A", "enderecado": 30}, {"produto_codigo": "B", "enderecado": 10}])
    assert list(out["pilhas"]) == ["86"]                       # órfã descartada
    assert out["divergencia"]["A"]["t"] == "falta"
    assert out["divergencia"]["B"]["t"] == "sobra"
    assert out["pilhas"]["86"][1]["nome"] == "PROD B"          # nome do mestre quando o rack veio sem
    assert len(out["posicoes"]) == 138


def test_exemplo_tem_todos_os_estados():
    d = dd.dados_exemplo()
    tipos = {v["t"] for v in d["divergencia"].values()}
    assert tipos == {"falta", "sobra"}
    assert any(len(p) == 4 for p in d["pilhas"].values())
    assert len(d["pilhas"]) < 138


# ── Loja ────────────────────────────────────────────────────────────────────
import loja as lj


def test_planta_da_loja():
    gond = [i for i in lj.ITENS if i["tipo"] == "gondola"]
    assert sorted(i["n"] for i in gond) == list(range(1, 13))
    assert {i["n"] for i in lj.ITENS if i["tipo"] == "estante"} == {1, 2, 6, 7, 8, 9, 13, 19, 20, 21, 22, 23, 24}
    # tudo dentro das paredes
    tol = 0.01   # a Estante Parede do Gondolas entra 5 mm na parede (x = 0,45, w = 0,55)
    for i in lj.ITENS:
        assert lj.PAREDE_ESP - tol <= i["x"] - i["w"] / 2 and i["x"] + i["w"] / 2 <= lj.LOJA_W - lj.PAREDE_ESP + tol
        assert lj.PAREDE_ESP - tol <= i["z"] - i["d"] / 2 and i["z"] + i["d"] / 2 <= lj.LOJA_H - lj.PAREDE_ESP + tol
    # o balcão encosta na parede da entrada (z = 14 - 0,18)
    bal = next(i for i in lj.ITENS if i["kind"] == "balcao")
    assert abs(bal["z"] + bal["d"] / 2 - (lj.LOJA_H - lj.PAREDE_ESP)) < 1e-9
    assert lj.numero_no_mapa("estante", 16) == 13 and lj.numero_no_mapa("gondola", 16) == 16
    assert abs(lj.ALTURA_GONDOLA - 0.6492) < 1e-3


def test_ilha_de_paletes():
    ilha = next(i for i in lj.ITENS if i["kind"] == "ilha")
    assert ilha["n"] == lj.ILHA == 22
    # no corredor central, entre a G7 (caixa) e a G6 (entrada), sem encostar em gôndola
    for gd in (i for i in lj.ITENS if i["tipo"] == "gondola"):
        dx = max(0.0, abs(gd["x"] - ilha["x"]) - ilha["w"] / 2)
        dz = max(0.0, abs(gd["z"] - ilha["z"]) - ilha["d"] / 2)
        assert math.hypot(dx, dz) - lj.GONDOLA_R > 0.2, gd["n"]
    est = [
        {"produto_codigo": "A", "produto_nome": "PROD A", "estante_num": 22, "nivel": 2, "coluna": 1},
        {"produto_codigo": "A", "produto_nome": "PROD A", "estante_num": 22, "nivel": 2, "coluna": 3},
    ]
    qtd = [
        {"produto_codigo": "A", "local_tipo": "estante", "local_num": 22, "face_ou_coluna": 1, "andar_ou_nivel": 2, "quantidade": 7},
        {"produto_codigo": "A", "local_tipo": "estante", "local_num": 22, "face_ou_coluna": 3, "andar_ou_nivel": 2, "quantidade": 4},
    ]
    out = lj.montar([], est, qtd)
    it = next(i for i in out["itens"] if i["kind"] == "ilha")
    assert it["rot"] == "Ilha" and it["faixas"] == 12 and it["ocupadas"] == 1
    assert [(p["loc"], p["q"]) for p in it["prod"]] == [("Espaço 3 · produto 2", 7), ("Espaço 3 · produto 4", 4)]


def test_mostruario():
    m = next(i for i in lj.ITENS if i["kind"] == "mostruario")
    assert m["n"] == lj.MOSTRUARIO == 23
    # na parede da direita, depois da E1 e antes da cozinha, sem encostar em gôndola nem na rota do cliente
    e1 = next(i for i in lj.ITENS if i["kind"] == "estante" and i["n"] == 1)
    cozinha = next(r for r in lj.REFERENCIAS if r[0] == "COZINHA")
    assert m["x"] + m["w"] / 2 < lj.LOJA_W - lj.PAREDE_ESP and lj.LOJA_W - lj.PAREDE_ESP - (m["x"] + m["w"] / 2) < 0.1
    assert m["z"] - m["d"] / 2 > e1["z"] + e1["d"] / 2 and m["z"] + m["d"] / 2 < cozinha[2]
    assert m["x"] - m["w"] / 2 > max(p[0] for r in lj.ROTAS for p in r) + 0.2
    for gd in (i for i in lj.ITENS if i["tipo"] == "gondola"):
        dx = max(0.0, abs(gd["x"] - m["x"]) - m["w"] / 2)
        dz = max(0.0, abs(gd["z"] - m["z"]) - m["d"] / 2)
        assert math.hypot(dx, dz) - lj.GONDOLA_R > 0.2, gd["n"]
    est = [
        {"produto_codigo": "P", "produto_nome": "PORCA 1/2", "estante_num": 23, "nivel": 6, "coluna": 0},
        {"produto_codigo": "R", "produto_nome": "RASTELO", "estante_num": 23, "nivel": 19, "coluna": 0},
    ]
    qtd = [
        {"produto_codigo": "P", "local_tipo": "estante", "local_num": 23, "face_ou_coluna": 0, "andar_ou_nivel": 6, "quantidade": 50},
        {"produto_codigo": "R", "local_tipo": "estante", "local_num": 23, "face_ou_coluna": 0, "andar_ou_nivel": 19, "quantidade": 3},
    ]
    out = lj.montar([], est, qtd)
    it = next(i for i in out["itens"] if i["kind"] == "mostruario")
    assert it["rot"] == "Mostruário" and it["faixas"] == 20 and it["ocupadas"] == 2
    assert [(p["loc"], p["q"]) for p in it["prod"]] == [("Posição 7", 50), ("Posição 20", 3)]


def test_expositor_de_madeira():
    m = next(i for i in lj.ITENS if i["kind"] == "madeira")
    assert m["n"] == lj.MADEIRA == 24
    # colado no balcão pelo lado do corredor e dentro do comprimento dele
    bal = next(i for i in lj.ITENS if i["kind"] == "balcao")
    assert abs((m["x"] - m["w"] / 2) - (bal["x"] + bal["w"] / 2)) < 1e-9
    assert bal["z"] - bal["d"] / 2 < m["z"] - m["d"] / 2 and m["z"] + m["d"] / 2 < bal["z"] + bal["d"] / 2
    est = [
        {"produto_codigo": "A", "produto_nome": "PROD A", "estante_num": 24, "nivel": 2, "coluna": 0},
        {"produto_codigo": "B", "produto_nome": "PROD B", "estante_num": 24, "nivel": 0, "coluna": 5},
    ]
    out = lj.montar([], est, [])
    it = next(i for i in out["itens"] if i["kind"] == "madeira")
    assert it["rot"] == "E24" and it["faixas"] == 3 and it["ocupadas"] == 2
    assert [p["loc"] for p in it["prod"]] == ["Degrau de baixo", "Degrau de cima"]


def test_rotas_nao_atravessam_estruturas():
    def ponto(rota, s):
        pts = list(rota) + [rota[0]]
        for a, b in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if s <= L:
                return a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L
            s -= L
        return pts[-1]
    for rota in lj.ROTAS:
        per = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(rota, list(rota[1:]) + [rota[0]]))
        s = 0.0
        while s < per:
            x, z = ponto(rota, s)
            for i in lj.ITENS:
                if i["tipo"] == "gondola":
                    assert math.hypot(x - i["x"], z - i["z"]) > lj.GONDOLA_R + 0.1
                else:
                    dx, dz = abs(x - i["x"]) - i["w"] / 2, abs(z - i["z"]) - i["d"] / 2
                    assert dx > 0.1 or dz > 0.1, (x, z, i["n"])
            s += 0.02


def test_face_da_gondola():
    # centro da face k = 90° − (k−1)·60° (face 1 voltada para +Z, numeração horária vista de cima)
    for k in range(1, 7):
        ang = math.radians(90 - 60 * (k - 1))
        assert lj.face_from_pos(math.cos(ang), math.sin(ang)) == k


def test_montar_loja_agrupa_e_ignora():
    gond = [
        {"produto_codigo": "A", "produto_nome": "PROD A", "gondola_num": 7, "andar": 0, "pos_x": 0, "pos_z": 1},
        {"produto_codigo": "A", "produto_nome": "PROD A", "gondola_num": 7, "andar": 0, "pos_x": 0, "pos_z": 1},  # duplicada
    ]
    est = [
        {"produto_codigo": "A", "produto_nome": "PROD A", "estante_num": 15, "nivel": 9},     # parede, nível limitado
        {"produto_codigo": "R", "produto_nome": "REMOVIDA", "estante_num": 3, "nivel": 1},    # estante removida
        {"produto_codigo": "N", "produto_nome": "NELLORE BASE", "estante_num": 19, "nivel": 0},  # base que saiu
    ]
    qtd = [
        {"produto_codigo": "A", "local_tipo": "gondola", "local_num": 7, "face_ou_coluna": 1, "andar_ou_nivel": 0, "quantidade": 30},
        {"produto_codigo": "A", "local_tipo": "estante", "local_num": 15, "face_ou_coluna": 0, "andar_ou_nivel": 5, "quantidade": 8},
        {"produto_codigo": "A", "local_tipo": "galpao", "local_num": 7, "face_ou_coluna": 0, "andar_ou_nivel": 1, "quantidade": 999},
    ]
    out = lj.montar(gond, est, qtd)
    g7 = next(i for i in out["itens"] if i["tipo"] == "gondola" and i["n"] == 7)
    assert len(g7["prod"]) == 1 and g7["prod"][0]["q"] == 30 and g7["prod"][0]["loc"] == "Face 1 · Base"
    parede = next(i for i in out["itens"] if i["kind"] == "parede")
    assert parede["prod"][0]["q"] == 8 and parede["prod"][0]["loc"] == "Seção 15 · Nível 6"
    assert [c["c"] for c in out["catalogo"]] == ["A"]          # removida e base do Nellore ficam de fora
    assert all(not i["prod"] for i in out["itens"] if i["kind"] in ("nellore",))


def test_exemplo_da_loja():
    import dados as dd2
    d = dd2.loja_exemplo()
    assert len(d["itens"]) == 25 and any(i["prod"] for i in d["itens"])


# ── Barracão ────────────────────────────────────────────────────────────────
import barracao as br


def test_barracao_padrao_100_paletes():
    pal = br.posicoes_padrao()
    assert len(pal) == 100 and pal[0]["rot"] == "BAR-01" and pal[-1]["rot"] == "BAR-100"
    assert br.colunas() == 25 and br.FILEIRAS == 4
    assert [br.z_da_fileira(i) for i in range(4)] == [930, 810, 310, 190]       # cm, do fundo para a frente
    assert br.corredor_livre() == 400                                           # corredor de manobra
    for p in pal:                                                               # tudo cabe entre as paredes
        assert 20 <= p["x"] - br.PALETE_X / 2 and p["x"] + br.PALETE_X / 2 <= 3480
        assert 20 <= p["z"] - br.PALETE_Z / 2 and p["z"] + br.PALETE_Z / 2 <= 980
    # a primeira fileira de frente deixa a folga das aberturas (500 cm livres na frente)
    assert br.z_da_fileira(3) - br.PALETE_Z / 2 == 140


def test_barracao_medidas_e_aberturas():
    assert (br.LARGURA, br.PROFUNDIDADE, br.PE_DIREITO) == (3500, 1000, 600)
    assert [(t, a, b, h) for t, a, b, h in br.ABERTURAS] == [("PORTA", 600, 800, 300), ("PORTÃO", 1300, 1800, 450), ("PORTA", 2300, 2500, 300)]
    d = br.montar(None)
    assert d["w"] == 35 and d["d"] == 10 and d["padrao"] and len(d["avisos"]) == 1


def test_montar_barracao_do_banco():
    linhas = [
        {"id": 1, "rotulo": "BAR-01", "pos_x": 130, "pos_z": 930, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 2},
        {"id": 2, "rotulo": "BAR-02", "pos_x": 265, "pos_z": 930, "produto_codigo": "", "produto_nome": "", "quantidade": 0},
        {"id": 3, "rotulo": "BAR-03", "pos_x": 130, "pos_z": 310, "produto_codigo": "B", "produto_nome": "PROD B", "quantidade": 1},
    ]
    d = br.montar(linhas)
    assert not d["padrao"] and d["avisos"] == [] and d["fileiras"] == 2
    assert d["pal"][0]["x"] == 1.3 and d["pal"][0]["z"] == 9.3 and d["pal"][0]["f"] == 1 and d["pal"][2]["f"] == 2
    assert [c["c"] for c in d["catalogo"]] == ["A", "B"]                         # palete livre não entra no catálogo
    assert len(br.montar([])["pal"]) == 100                                      # tabela vazia → layout padrão


def test_barracao_pilha_de_gaiolas():
    linhas = [
        {"id": 1, "rotulo": "BAR-01", "pos_x": 130, "pos_z": 930, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 2},
        {"id": 2, "rotulo": "BAR-02", "pos_x": 265, "pos_z": 930, "produto_codigo": "", "produto_nome": "", "quantidade": 0},
    ]
    gaiolas = [
        {"endereco_id": 1, "nivel": 3, "produto_codigo": "C", "produto_nome": "PROD C", "quantidade": 5},
        {"endereco_id": 1, "nivel": 2, "produto_codigo": "EST:9", "produto_nome": "X · ANA", "quantidade": 1},
        {"endereco_id": 2, "nivel": 2, "produto_codigo": "D", "produto_nome": "PROD D", "quantidade": 7},
    ]
    d = br.montar(linhas, gaiolas)
    p1, p2 = d["pal"]
    assert [(g["nv"], g["c"]) for g in br.gaiolas_do(p1)] == [(1, "A"), (2, "EST:9"), (3, "C")]
    assert p1["g"][0]["e"] is True                                               # estocado também na gaiola de cima
    # chão vazio com gaiola em cima: a de baixo vai para o chão
    assert p2["c"] == "D" and p2["g"] == []
    assert {c["c"] for c in d["catalogo"]} == {"A", "C", "D", "EST:9"}
    assert d["gaiolasMax"] == br.GAIOLAS_MAX == 4
    assert br.rotulo_gaiola("BAR-01", 3) == "BAR-01 · N3" and br.rotulo_gaiola("BAR-01", 1) == "BAR-01"
    # banco de antes da pilha: sem a tabela de gaiolas, só o chão
    assert br.montar(linhas, None)["pal"][0]["g"] == []


def test_barracao_pilha_na_busca_global_e_na_capacidade():
    import dados as ddp
    t = ddp.tudo_exemplo()
    t["barracao"] = br.montar(
        [{"id": 1, "rotulo": "BAR-01", "pos_x": 130, "pos_z": 930, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 2}],
        [{"endereco_id": 1, "nivel": 2, "produto_codigo": "B", "produto_nome": "PROD B", "quantidade": 1}])
    idx = [e for e in ddp.indice_global(t["galpao"], t["loja"], t["barracao"]) if e["a"] == "barracao"]
    assert [(e["c"], e["w"]) for e in idx] == [("A", "BAR-01"), ("B", "BAR-01 · N2")]
    assert ddp.ocupacao_barracao(t["barracao"]) == ddp.percentual(2, 4)       # 2 gaiolas de 1 palete × 4


def test_barracao_exemplo():
    import dados as ddb
    d = ddb.barracao_exemplo()
    assert len(d["pal"]) == 100 and any(p["c"] for p in d["pal"]) and any(not p["c"] for p in d["pal"])
    assert any(p["g"] for p in d["pal"]) and all(len(br.gaiolas_do(p)) <= br.GAIOLAS_MAX for p in d["pal"])


# ── Busca global ────────────────────────────────────────────────────────────


def test_indice_global_junta_os_tres_mapas():
    import dados as ddg
    t = ddg.tudo_exemplo()
    idx = ddg.indice_global(t["galpao"], t["loja"], t["barracao"])
    areas = {e["a"] for e in idx}
    assert areas == {"galpao", "loja", "barracao"}
    assert all(e["c"].strip() and "n" in e and "w" in e for e in idx)
    # um mesmo produto aparece em mais de um mapa (é isso que a busca global resume)
    por_codigo: dict[str, set] = {}
    for e in idx:
        por_codigo.setdefault(e["c"], set()).add(e["a"])
    assert any(len(a) == 3 for a in por_codigo.values())


def test_ler_tudo_isola_o_mapa_que_falha(monkeypatch):
    import dados as ddg
    # galpão sem leitura (racks None) → só ele vira exemplo; os outros seguem
    res = [None, None, None, None, None, None, [], [], [], [], [], None]
    monkeypatch.setattr(ddg, "consultar", lambda url, token, sqls: res)
    t = ddg.ler_tudo("http://x", "t")
    assert "galpao" in t["erros"] and "loja" not in t["erros"]
    assert len(t["galpao"]["posicoes"]) == 138          # exemplo no lugar


# ── Escada para o mesanino ──────────────────────────────────────────────────


def test_escada_paralela_a_rua_1_do_14_ao_11():
    e = g.escada()
    p14, p11, p1 = g.POSICAO_POR_NUMERO[14], g.POSICAO_POR_NUMERO[11], g.POSICAO_POR_NUMERO[1]
    assert e["parte"] == 1 and (e["de"], e["ate"]) == (14, 11)
    # base junto ao 14 e topo junto ao 11: cobre as quatro posições 14, 13, 12 e 11
    assert abs(e["z0"] - (p14.z - p14.tamanho_z / 2)) < 1e-6 and abs(e["z1"] - (p11.z + p11.tamanho_z / 2)) < 1e-6
    assert e["sentido"] == 1 and e["z1"] > e["z0"]
    # do lado oposto ao corredor (o corredor da Rua 1 fica a oeste, então a escada fica a leste dos racks)
    assert g.POSICAO_POR_NUMERO[1].rua.lado_corredor == -1
    assert e["x0"] > p14.x + p14.tamanho_x / 2 and e["lado"] == 1
    assert abs((e["x1"] - e["x0"]) - g.ESCADA_LARGURA) < 1e-6
    # termina na altura do 3º nível: palete + 2 passos de nível + um rack
    assert abs(e["altura"] - (0.12 + 2 * g.PASSO_NIVEL + g.ALTURA_NIVEL)) < 1e-6
    # não invade nenhum rack da Rua 1
    for n in range(1, 15):
        p = g.POSICAO_POR_NUMERO[n]
        assert p.x + p.tamanho_x / 2 <= e["x0"]


def test_escada_vai_no_json_do_galpao():
    import dados as dde
    assert dde.dados_exemplo()["escada"]["parte"] == 1


# ── Chuveiro lava-olhos ─────────────────────────────────────────────────────


def test_lava_olhos_alinhado_a_rua_2_alem_do_25():
    lv = g.lava_olhos()
    p25 = g.POSICAO_POR_NUMERO[25]
    assert lv["parte"] == 1 and lv["rua"] == 2 and lv["z"] == p25.z                    # na linha da Rua 2
    assert lv["x"] < p25.x - p25.tamanho_x / 2                                         # a oeste da ponta da fileira
    assert abs(lv["altura"] - (0.12 + g.PASSO_NIVEL + g.ALTURA_NIVEL)) < 1e-6          # topo de 2 níveis
    # longe o bastante de qualquer rack (a cabeça do chuveiro avança ~0,9 m para o lado)
    for p in g.POSICOES:
        assert not (abs(p.x - lv["x"]) < p.tamanho_x / 2 + 0.9 and abs(p.z - lv["z"]) < p.tamanho_z / 2 + 0.3), p.numero


def test_lava_olhos_vai_no_json_do_galpao():
    import dados as ddl
    assert ddl.dados_exemplo()["lavaolhos"]["niveis"] == 2


# ── Ocupação em porcentagem ─────────────────────────────────────────────────


def test_percentual_arredonda_e_protege_divisao_por_zero():
    import dados as ddp
    assert ddp.percentual(1, 2) == 50 and ddp.percentual(97, 129) == 75 and ddp.percentual(0, 10) == 0
    assert ddp.percentual(1, 8) == 13        # 12,5 → 13 (metade para cima)
    assert ddp.percentual(5, 0) == 0


def test_ocupacao_do_galpao_por_parte():
    import dados as ddp
    # 2 racks na posição 1 e 1 na 2 (Parte 1); 1 na 86 (Parte 2)
    linhas = [
        {"posicao": 1, "ordem": 1, "produto_codigo": "A", "produto_nome": "A", "quantidade": 1},
        {"posicao": 1, "ordem": 2, "produto_codigo": "A", "produto_nome": "A", "quantidade": 1},
        {"posicao": 2, "ordem": 1, "produto_codigo": "B", "produto_nome": "B", "quantidade": 1},
        {"posicao": 86, "ordem": 1, "produto_codigo": "C", "produto_nome": "C", "quantidade": 1},
    ]
    oc = ddp.ocupacao_galpao(ddp.montar(linhas, [], {}, []))
    assert set(oc) == {1, 2}
    assert oc[1] == {"racks": 3, "capacidade": 85 * 4, "pct": ddp.percentual(3, 340)}      # Parte 1: 85 posições
    assert oc[2] == {"racks": 1, "capacidade": 53 * 4, "pct": ddp.percentual(1, 212)}      # Parte 2: 44 + 9 gaiolas


def test_ocupacao_da_loja_por_faixas_de_endereco():
    import loja as ljt, dados as ddp
    # 12 gôndolas × 18 (3 andares × 6 faces) + estantes por nível + Estante Parede 6 × 6 + ilha (12) + mostruário (20)
    # + Expositor de Madeira (3 degraus)
    out = ljt.montar([], [], [])
    assert sum(i["faixas"] for i in out["itens"]) == 12 * 18 + (4 + 6 + 7 + 6 + 4 + 5 + 4 + 4) + 36 + 12 + 20 + 3
    assert next(i for i in out["itens"] if i["kind"] == "balcao")["faixas"] == 0
    # duas faces/andares na G7 (a mesma face e andar com 2 produtos conta uma vez) e um nível na E1
    gond = [
        {"produto_codigo": "A", "produto_nome": "A", "gondola_num": 7, "andar": 0, "pos_x": 0, "pos_z": 1},
        {"produto_codigo": "B", "produto_nome": "B", "gondola_num": 7, "andar": 0, "pos_x": 0, "pos_z": 1},
        {"produto_codigo": "A", "produto_nome": "A", "gondola_num": 7, "andar": 2, "pos_x": 0, "pos_z": 1},
    ]
    est = [{"produto_codigo": "A", "produto_nome": "A", "estante_num": 1, "nivel": 3}]
    o = ddp.ocupacao_loja(ljt.montar(gond, est, []))
    assert o["ocupadas"] == 3 and o["total"] == 327 and o["pct"] == ddp.percentual(3, 327)


def test_capacidades_independentes_de_cada_area():
    import dados as ddp
    caps = ddp.capacidades(ddp.tudo_exemplo())
    assert [c["nome"] for c in caps] == ["Galpão 1", "Galpão 2", "Barracão", "Loja"]
    assert all(0 <= c["pct"] <= 100 and c["dica"] for c in caps)


# ── Mesa de expedição ───────────────────────────────────────────────────────


def test_mesa_na_ponta_da_rua_12_alem_do_119():
    m = g.mesa()
    p = g.POSICAO_POR_NUMERO[119]
    assert m["parte"] == 2 and m["rua"] == 12
    assert m["z0"] > p.z + p.tamanho_z / 2                                   # depois da ponta do 119
    assert abs((m["z1"] - m["z0"]) - g.MESA_COMPRIMENTO) < 1e-6
    assert abs((m["x1"] - m["x0"]) - (g.MESA_PROFUNDIDADE + g.GAVETEIRO_AVANCO)) < 1e-6
    for q in g.POSICOES:                                                     # não invade nenhum rack
        assert not (m["x0"] < q.x + q.tamanho_x / 2 and m["x1"] > q.x - q.tamanho_x / 2
                    and m["z0"] < q.z + q.tamanho_z / 2 and m["z1"] > q.z - q.tamanho_z / 2), q.numero


def test_mesa_vai_no_json_do_galpao():
    import dados as ddm
    assert ddm.dados_exemplo()["mesa"]["gaveteiro"]["gavetas"] == 3


# ── Empilhadeira (modelo 3D) ────────────────────────────────────────────────


def test_empilhadeira_em_frente_a_mesa_dentro_do_piso():
    e, m = g.empilhadeira(), g.mesa()
    assert (e["parte"], e["rua"]) == (m["parte"], m["rua"])
    borda = m["z_ini"] + m["sentido"] * m["comprimento_total"]               # o piso do Galpão 2 termina na mesa
    tras = e["z1"] if m["sentido"] > 0 else e["z0"]
    assert abs((borda - tras) * m["sentido"] - g.EMPILHADEIRA_RECUO) < 1e-6
    assert abs((e["z1"] - e["z0"]) - (g.EMPILHADEIRA_TRAS + g.EMPILHADEIRA_FRENTE)) < 1e-6
    lado = e["x0"] - m["x1"] if m["frente"] > 0 else m["x0"] - e["x1"]       # na frente da mesa, com folga
    assert abs(lado - g.EMPILHADEIRA_FOLGA) < 1e-6
    assert e["x1"] < 17.5                                                    # antes da rampa (RAMPA.x0 em cena.html)
    for q in g.POSICOES:                                                     # não invade nenhum rack
        assert not (e["x0"] < q.x + q.tamanho_x / 2 and e["x1"] > q.x - q.tamanho_x / 2
                    and e["z0"] < q.z + q.tamanho_z / 2 and e["z1"] > q.z - q.tamanho_z / 2), q.numero


def test_empilhadeiras_apontam_para_glb_que_existem():
    from pathlib import Path
    import dados as ddm
    emps = ddm.dados_exemplo()["empilhadeiras"]
    assert [e["nome"] for e in emps] == ["Empilhadeira patolada", "Empilhadeira contrabalançada"]
    for e in emps:
        assert e["modelo"].startswith("app/static/")                         # servido pelo enableStaticServing
        assert (Path(__file__).resolve().parent.parent / e["modelo"].removeprefix("app/")).is_file()


def test_contrabalancada_no_corredor_de_carregamento():
    e, c, m = g.contrabalancada(), g.corredor(), g.mesa()
    assert e["corredor"] and e["parte"] == c["parte"] == m["parte"]
    fora = sorted((c["borda"], c["borda"] + c["sentido"] * c["profundidade"]))
    assert fora[0] < e["z0"] and e["z1"] < fora[1]                           # inteira dentro da faixa do corredor
    assert abs((e["x1"] - e["x0"]) - (g.CONTRABALANCADA_TRAS + g.CONTRABALANCADA_FRENTE)) < 1e-6   # paralela à frente
    ps = [q for q in g.POSICOES if q.parte == c["parte"]]
    assert min(q.x for q in ps) < e["x0"] and e["x1"] < max(q.x for q in ps)  # dentro da largura do galpão
    import math
    garfo = (math.sin(e["rot"]), math.cos(e["rot"]))                          # +Z do modelo depois da rotação
    assert garfo[0] * m["frente"] < -0.99                                     # garfo para o lado da mesa
    assert e["cores"] == {g.CONTRABALANCADA_MATERIAL_COR: g.CONTRABALANCADA_COR}   # amarela, como a da loja



# ── Rack misto (até 5 produtos no mesmo palete, no Gondolas) ───────────────


def test_rack_misto_entra_no_rack_no_saldo_e_na_busca():
    racks = [
        {"posicao": 52, "ordem": 1, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 10},
        {"posicao": 52, "ordem": 2, "produto_codigo": "B", "produto_nome": "PROD B", "quantidade": 5},
    ]
    itens = [
        {"posicao": 52, "ordem": 1, "produto_codigo": "X", "produto_nome": "", "quantidade": 3},
        {"posicao": 52, "ordem": 1, "produto_codigo": "Y", "produto_nome": "PROD Y", "quantidade": 2},
        {"posicao": 999, "ordem": 1, "produto_codigo": "Z", "produto_nome": "ORFAO", "quantidade": 1},
    ]
    mestre = [
        {"codigo": "A", "produto": "PROD A", "qtd_sistema": 10},
        {"codigo": "X", "produto": "PROD X DO MESTRE", "qtd_sistema": 9},
        {"codigo": "Y", "produto": "PROD Y", "qtd_sistema": 2},
    ]
    end = [{"produto_codigo": c, "enderecado": q} for c, q in (("A", 10), ("B", 5), ("X", 3), ("Y", 2))]
    out = dd.montar(racks, mestre, {}, end, itens)
    base, cima = out["pilhas"]["52"]
    assert [(i["c"], i["nome"], i["q"]) for i in base["it"]] == [("X", "PROD X DO MESTRE", 3.0), ("Y", "PROD Y", 2.0)]
    assert "it" not in cima
    # O item com falta entra na divergência como qualquer produto de rack.
    assert out["divergencia"]["X"]["t"] == "falta" and "Y" not in out["divergencia"]
    assert {c["c"] for c in out["catalogo"]} >= {"A", "B", "X", "Y"}
    assert "Z" not in {c["c"] for c in out["catalogo"]}            # item de rack fora da leitura fica de fora
    idx = dd.indice_global(out, {"itens": []}, {"pal": []})
    assert {(i["c"], i["w"]) for i in idx} == {("A", "52"), ("B", "52"), ("X", "52"), ("Y", "52")}


def test_sem_tabela_de_itens_o_galpao_segue_so_com_os_racks():
    racks = [{"posicao": 52, "ordem": 1, "produto_codigo": "A", "produto_nome": "PROD A", "quantidade": 10}]
    out = dd._montar_galpao_de(racks, None, [], None, None, [], None)
    assert "it" not in out["pilhas"]["52"][0]


def test_exemplo_tem_um_rack_misto():
    d = dd.dados_exemplo()
    mistos = [r for p in d["pilhas"].values() for r in p if r.get("it")]
    assert len(mistos) == 1 and len(mistos[0]["it"]) == 2
