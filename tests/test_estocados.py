import barracao as br
import dados as dd
import estocados as es

LINHAS = [
    {"razao_social": "JOÃO SILVA", "descricao": "HERBICIDA BORAL 500 SC 20L", "codigo": "254185", "saldo": "30"},
    {"cooperado": "Maria Souza", "produto": "ADUBO FOLIAR 5L", "cod": "410077", "saldo": "12,5"},
    {"cliente": "Fazenda Boa Vista", "descricao": "SAL MINERAL", "saldo": "40"},
    {"razao_social": "ZERADO", "descricao": "X", "codigo": "1", "saldo": "0"},
]


def itens():
    return [es.item_de_linha(l) for l in LINHAS]


def test_item_de_linha_aceita_sinonimos_e_virgula():
    a, b, c, _ = itens()
    assert (a.cooperado, a.produto, a.codigo, a.saldo) == ("JOÃO SILVA", "HERBICIDA BORAL 500 SC 20L", "254185", 30)
    assert (b.cooperado, b.produto, b.codigo, b.saldo) == ("Maria Souza", "ADUBO FOLIAR 5L", "410077", 12.5)
    assert c.cooperado == "Fazenda Boa Vista" and c.codigo == ""


def test_busca_sem_acento_sem_maiuscula_e_varios_termos():
    its = itens()
    assert [i.codigo for i in es.buscar_estocados("joao", its)] == ["254185"]
    assert [i.codigo for i in es.buscar_estocados("SILVA boral", its)] == ["254185"]
    assert [i.codigo for i in es.buscar_estocados("410077 maria", its)] == ["410077"]
    assert es.buscar_estocados("silva adubo", its) == []   # termos em itens diferentes não cruzam
    assert len(es.buscar_estocados("  ", its)) == len(its)  # vazia devolve tudo


def test_codigo_e_nome_do_palete():
    a, _, c, _ = itens()
    assert a.codigo_do_palete == "EST:254185"
    assert a.nome_do_palete == "HERBICIDA BORAL 500 SC 20L · JOÃO SILVA"
    assert c.codigo_do_palete == "EST:SAL MINERAL"  # sem código usa o nome do produto


def test_ligacao_palete_item_pelo_nome_e_nao_pelo_codigo():
    # dois cooperados com o mesmo produto/código: só o nome diferencia
    j = es.item_de_linha({"razao_social": "JOAO", "descricao": "BORAL", "codigo": "9", "saldo": "1"})
    m = es.item_de_linha({"razao_social": "MARIA", "descricao": "BORAL", "codigo": "9", "saldo": "1"})
    assert j.codigo_do_palete == m.codigo_do_palete
    mapa = es.enderecos_dos_estocados(
        [{"posicao": 40, "ordem": 4, "codigo": j.codigo_do_palete, "nome": j.nome_do_palete},
         {"posicao": 12, "ordem": 1, "codigo": "254185", "nome": j.nome_do_palete}],  # loja: ignorado
        [{"rotulo": "BAR-07", "codigo": j.codigo_do_palete, "nome": j.nome_do_palete}],
    )
    assert mapa == {j.nome_do_palete: ["Galpão 40 · N4", "BAR-07"]}
    assert m.nome_do_palete not in mapa


def test_para_cena_tem_enderecos_e_ignora_saldo_zero():
    a = itens()[0]
    racks = [(40, {"o": 4, "c": a.codigo_do_palete, "nome": a.nome_do_palete})]
    out = es.para_cena(LINHAS, racks, [])
    assert out["ok"] and len(out["itens"]) == 3
    assert out["itens"][0]["end"] == ["Galpão 40 · N4"] and out["itens"][1]["end"] == []
    assert es.para_cena(None, racks, [])["ok"] is False


def test_resumo_de_ocupacao():
    assert es.resumo_ocupacao(516, ["EST:1"] * 30 + ["254185"] * 61) == "425 livres · 30 estocados · 61 loja"
    assert es.resumo_ocupacao(10, ["EST:1", "EST:2"]) == "8 livres · 2 estocados"
    assert es.resumo_ocupacao(10, ["A", "B", "C"]) == "7 livres · 3 loja"
    assert es.resumo_ocupacao(516, []) == "516 livres"
    assert es.resumo_ocupacao(2, ["A", "EST:1"]) == "0 livres · 1 estocados · 1 loja"


def test_resumo_do_galpao_usa_posicoes_vezes_niveis():
    t = dd.tudo_exemplo()["galpao"]
    assert len(t["posicoes"]) * t["geo"]["niveisMax"] == 516
    assert dd.resumo_galpao(t).split(" livres")[0] == str(516 - sum(len(p) for p in t["pilhas"].values()))


def test_est_nao_gera_espelho_em_estoque_localizado():
    assert es.deve_espelhar("EST:254185") is False
    assert es.deve_espelhar("EST:SAL MINERAL") is False
    assert es.deve_espelhar("254185") is True
    assert es.deve_espelhar("") is True and es.deve_espelhar(None) is True
    assert es.deve_espelhar("US254185") is True  # só o prefixo exato conta


def test_est_fica_fora_do_saldo_e_da_divergencia():
    racks = [
        {"posicao": 1, "ordem": 1, "produto_codigo": "EST:254185", "produto_nome": "BORAL · JOAO", "quantidade": 30},
        {"posicao": 2, "ordem": 1, "produto_codigo": "254185", "produto_nome": "BORAL", "quantidade": 10},
    ]
    mestre = [{"codigo": "254185", "produto": "BORAL", "qtd_sistema": 10}]
    out = dd.montar(racks, mestre, {}, [{"produto_codigo": "254185", "enderecado": 10}])
    assert out["divergencia"] == {}                      # os 30 do estocado não somam em 254185
    assert [r["e"] for r in out["pilhas"]["1"]] == [True]
    assert [r["e"] for r in out["pilhas"]["2"]] == [False]
    assert any(c["c"] == "EST:254185" for c in out["catalogo"])


def test_est_nao_vira_divergencia_mesmo_com_nome_igual_no_mestre():
    racks = [{"posicao": 1, "ordem": 1, "produto_codigo": "EST:1", "produto_nome": "X · Y", "quantidade": 5}]
    out = dd.montar(racks, [{"codigo": "EST:1", "produto": "X · Y", "qtd_sistema": 99}], {}, [])
    assert out["divergencia"] == {}


def test_barracao_marca_estocado():
    out = br.montar([
        {"id": 1, "rotulo": "BAR-01", "pos_x": 100, "pos_z": 100, "produto_codigo": "EST:9", "produto_nome": "A · B", "quantidade": 1},
        {"id": 2, "rotulo": "BAR-02", "pos_x": 300, "pos_z": 100, "produto_codigo": "123", "produto_nome": "C", "quantidade": 1},
    ])
    assert [p["e"] for p in out["pal"]] == [True, False]


def test_ler_tudo_sem_materiais_terceiros_nao_derruba(monkeypatch):
    t = dd.tudo_exemplo()
    assert t["estocados"]["ok"] and any(i["end"] for i in t["estocados"]["itens"])
    vazio = dd.estocados_da_cena(None, t["galpao"], t["barracao"])
    assert vazio == {"ok": False, "itens": [], "cor": es.COR_ESTOCADO}


def test_exemplo_nao_cria_divergencia_para_estocado():
    t = dd.tudo_exemplo()
    assert not any(k.startswith("EST:") for k in t["galpao"]["divergencia"])


def test_mesmo_codigo_em_dois_cooperados_nao_troca_o_nome():
    # EST:42200 é o mesmo código para dois cooperados: o nome do palete é o que liga ao item
    racks = [
        {"posicao": 45, "ordem": 2, "produto_codigo": "EST:42200", "produto_nome": "ROUNDUP 20L · ANA", "quantidade": 10},
        {"posicao": 46, "ordem": 1, "produto_codigo": "EST:42200", "produto_nome": "ROUNDUP 20L · MARCELO", "quantidade": 45},
    ]
    out = dd.montar(racks, [], {}, [])
    assert out["pilhas"]["45"][0]["nome"] == "ROUNDUP 20L · ANA"
    assert out["pilhas"]["46"][0]["nome"] == "ROUNDUP 20L · MARCELO"
    assert [c["n"] for c in out["catalogo"] if c.get("e")] == ["ROUNDUP 20L · ANA", "ROUNDUP 20L · MARCELO"]
    linhas = [
        {"razao_social": "MARCELO", "descricao": "ROUNDUP 20L", "codigo": "42200", "saldo": "99"},
        {"razao_social": "ANA", "descricao": "ROUNDUP 20L", "codigo": "42200", "saldo": "10"},
    ]
    itens = {i["coop"]: i["end"] for i in dd.estocados_da_cena(linhas, out, br.montar(None))["itens"]}
    assert itens == {"MARCELO": ["Galpão 46 · N1"], "ANA": ["Galpão 45 · N2"]}


def test_catalogo_do_barracao_tem_um_estocado_por_cooperado():
    out = br.montar([
        {"id": 1, "rotulo": "BAR-01", "pos_x": 100, "pos_z": 100, "produto_codigo": "EST:9", "produto_nome": "A · ANA", "quantidade": 1},
        {"id": 2, "rotulo": "BAR-02", "pos_x": 300, "pos_z": 100, "produto_codigo": "EST:9", "produto_nome": "A · BIA", "quantidade": 1},
        {"id": 3, "rotulo": "BAR-03", "pos_x": 500, "pos_z": 100, "produto_codigo": "123", "produto_nome": "C", "quantidade": 1},
    ])
    assert out["catalogo"] == [{"c": "123", "n": "C"}, {"c": "EST:9", "n": "A · ANA", "e": True}, {"c": "EST:9", "n": "A · BIA", "e": True}]


def test_mesmo_produto_do_mesmo_cooperado_soma_o_saldo():
    linhas = [
        {"razao_social": "BRAVO", "descricao": "BORAL 20L", "codigo": "254185", "saldo": "40"},
        {"razao_social": "BRAVO", "descricao": "BORAL 20L", "codigo": "254185", "saldo": "22"},
        {"razao_social": "BRAVO", "descricao": "BORAL 20L", "codigo": "254185", "saldo": "107"},
        {"razao_social": "OUTRO", "descricao": "BORAL 20L", "codigo": "254185", "saldo": "5"},
        {"razao_social": "BRAVO", "descricao": "VANTACOR 5L", "codigo": "9", "saldo": "12"},
        {"razao_social": "BRAVO", "descricao": "VANTACOR 5L", "codigo": "9", "saldo": "0"},  # saldo 0 não conta
    ]
    racks = [(7, {"o": 1, "c": "EST:254185", "nome": "BORAL 20L · BRAVO"})]
    itens = es.para_cena(linhas, racks, [])["itens"]
    por = {(i["coop"], i["prod"]): i for i in itens}
    assert len(itens) == 3
    b = por[("BRAVO", "BORAL 20L")]
    assert (b["saldo"], b["n"], b["end"]) == (169, 3, ["Galpão 7 · N1"])  # 40 + 22 + 107, um endereço só
    assert por[("OUTRO", "BORAL 20L")]["saldo"] == 5 and por[("OUTRO", "BORAL 20L")]["end"] == []
    assert por[("BRAVO", "VANTACOR 5L")]["n"] == 1
