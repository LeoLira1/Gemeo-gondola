import loja as lj


def test_caixas_vao_para_a_estrutura_com_posicao_e_cor():
    gond = [{"produto_codigo": "A1", "produto_nome": "A", "gondola_num": 7, "andar": 1,
             "pos_x": 1.2, "pos_z": -0.5, "cor_hex": "#2e7d4f"}]
    est = [
        {"produto_codigo": "B1", "produto_nome": "B", "estante_num": 15, "nivel": 2, "coluna": 1, "slot": 3,
         "cor_hex": "#8b1a1a"},
        {"produto_codigo": "C1", "produto_nome": "C", "estante_num": 1, "nivel": 0, "coluna": 0, "slot": 0,
         "cor_hex": None},
    ]
    d = lj.montar(gond, est, [])
    por_rot = {i["rot"]: i for i in d["itens"]}

    assert por_rot["G7"]["cx"] == [{"c": "A1", "h": "#2e7d4f", "a": 1, "x": 1.2, "z": -0.5}]
    # a seção 15 da Estante Parede cai no retângulo único E13–18, guardando o número da seção
    assert por_rot["E13–18"]["cx"] == [{"c": "B1", "h": "#8b1a1a", "e": 15, "col": 1, "niv": 2, "s": 3}]
    # sem cor gravada, o cinza do app
    assert por_rot["E1"]["cx"][0]["h"] == "#888888"
    assert por_rot["G1"]["cx"] == []


def test_cor_caixa_rejeita_lixo():
    assert lj.cor_caixa("#ABCDEF") == "#ABCDEF"
    assert lj.cor_caixa("red") == "#888888"
    assert lj.cor_caixa("#12345G") == "#888888"
