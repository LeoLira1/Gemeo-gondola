import math

import galpao as g
import dados as dd


def test_planta_129_posicoes_85_44():
    assert g.TOTAL_POSICOES == 129
    assert sorted(p.numero for p in g.POSICOES) == list(range(1, 130))
    assert sum(1 for p in g.POSICOES if p.parte == 1) == 85
    assert sum(1 for p in g.POSICOES if p.parte == 2) == 44
    assert len(g.RUAS) == 12
    assert {r.numero for r in g.RUAS if r.parte == 2} == {9, 10, 11, 12}
    assert min(p.numero for p in g.POSICOES if p.parte == 2) == 86


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
    assert len(out["posicoes"]) == 129


def test_exemplo_tem_todos_os_estados():
    d = dd.dados_exemplo()
    tipos = {v["t"] for v in d["divergencia"].values()}
    assert tipos == {"falta", "sobra"}
    assert any(len(p) == 4 for p in d["pilhas"].values())
    assert len(d["pilhas"]) < 129


# ── Loja ────────────────────────────────────────────────────────────────────
import loja as lj


def test_planta_da_loja():
    gond = [i for i in lj.ITENS if i["tipo"] == "gondola"]
    assert sorted(i["n"] for i in gond) == list(range(1, 13))
    assert {i["n"] for i in lj.ITENS if i["tipo"] == "estante"} == {1, 2, 6, 7, 8, 9, 13, 19, 20, 21}
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
    assert len(d["itens"]) == 22 and any(i["prod"] for i in d["itens"])


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


def test_barracao_exemplo():
    import dados as ddb
    d = ddb.barracao_exemplo()
    assert len(d["pal"]) == 100 and any(p["c"] for p in d["pal"]) and any(not p["c"] for p in d["pal"])


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
    res = [None, None, None, None, None, None, [], [], [], []]
    monkeypatch.setattr(ddg, "consultar", lambda url, token, sqls: res)
    t = ddg.ler_tudo("http://x", "t")
    assert "galpao" in t["erros"] and "loja" not in t["erros"]
    assert len(t["galpao"]["posicoes"]) == 129          # exemplo no lugar


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


def test_ocupacao_do_galpao_vagas_e_capacidade():
    import dados as ddp
    out = ddp.montar(
        [{"posicao": 1, "ordem": 1, "produto_codigo": "A", "produto_nome": "A", "quantidade": 1},
         {"posicao": 1, "ordem": 2, "produto_codigo": "A", "produto_nome": "A", "quantidade": 1},
         {"posicao": 2, "ordem": 1, "produto_codigo": "B", "produto_nome": "B", "quantidade": 1}],
        [], {}, [])
    oc = ddp.ocupacao_galpao(out)
    assert oc["vagas"] == ddp.percentual(2, 129)          # 2 de 129 posições
    assert oc["capacidade"] == ddp.percentual(3, 129 * 4)  # 3 racks de 516


def test_ocupacao_barracao_e_loja_do_exemplo():
    import dados as ddp
    b = ddp.barracao_exemplo()
    assert ddp.ocupacao_barracao(b) == ddp.percentual(sum(1 for p in b["pal"] if p["c"]), 100)
    assert 0 <= ddp.ocupacao_loja(ddp.loja_exemplo()) <= 100
