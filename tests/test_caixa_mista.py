import dados as dd
import loja as lj


def _linha(cod, nome, num=13, col=0, niv=2, slot=5, caixa_nome=None):
    r = {"produto_codigo": cod, "produto_nome": nome, "estante_num": num, "coluna": col, "nivel": niv, "slot": slot}
    if caixa_nome is not None:
        r["caixa_nome"] = caixa_nome
    return r


def test_caixa_mista_e_mais_de_uma_linha_no_mesmo_slot_na_ordem_do_id():
    est = [
        _linha("B", "BICO", caixa_nome="Peças Hoppner"),
        _linha("X", "SOZINHO", slot=0),
        _linha("A", "ANEL"),
        _linha("B", "BICO"),                           # repetido na mesma caixa: conta uma vez
    ]
    cx = lj.caixas_mistas(est)
    assert list(cx) == [(13, 0, 2, 5)]
    assert cx[(13, 0, 2, 5)]["codigos"] == ["B", "A"]  # a fatia de cima é a do primeiro
    assert cx[(13, 0, 2, 5)]["nome"] == "Peças Hoppner"


def test_banco_sem_coluna_caixa_nome_nao_quebra():
    # Antes do app novo abrir no banco, estante_layout não tem caixa_nome (o SELECT * só não traz a chave).
    cx = lj.caixas_mistas([_linha("A", "ANEL"), _linha("B", "BICO")])
    assert cx[(13, 0, 2, 5)]["nome"] is None


def test_montar_poe_a_caixa_na_estrutura_do_mapa_com_quantidade_e_saldo():
    est = [_linha("A", "ANEL", num=14, caixa_nome="Peças"), _linha("B", "BICO", num=14), _linha("C", "CANO", num=14, slot=0)]
    qtd = [{"produto_codigo": "A", "local_tipo": "estante", "local_num": 14, "face_ou_coluna": 0,
            "andar_ou_nivel": 2, "quantidade": 6}]
    loja = lj.montar([], est, qtd, {"A": "falta", "B": "ok"})
    parede = next(i for i in loja["itens"] if i["n"] == lj.PAREDE_MIN)
    [cx] = parede["mistas"]
    assert cx["nome"] == "Peças" and cx["e"] == 14 and cx["s"] == 5
    assert cx["loc"] == "Seção 14 · Nível 3 · slot 6"
    assert [(p["c"], p["q"], p["st"]) for p in cx["pr"]] == [("A", 6.0, "falta"), ("B", None, "ok")]
    # Os produtos da caixa apontam para ela; o da caixa comum, não.
    por_cod = {p["c"]: p for p in parede["prod"]}
    assert por_cod["A"]["mx"] == 0 and por_cod["B"]["mx"] == 0 and "mx" not in por_cod["C"]
    # Na lista de caixas físicas as linhas continuam uma por produto: a cena junta as do mesmo slot.
    assert [(k["c"], k["s"]) for k in parede["cx"]] == [("A", 5), ("B", 5), ("C", 0)]
    assert loja["caixaMax"] == 5


def test_estruturas_de_um_produto_por_endereco_nao_tem_caixa_mista():
    est = [_linha("A", "ANEL", num=lj.ILHA, slot=0), _linha("B", "BICO", num=lj.ILHA, slot=0)]
    loja = lj.montar([], est, [])
    assert all(not i["mistas"] for i in loja["itens"])


def test_saldo_das_caixas_segue_a_regra_do_galpao():
    est = [_linha("A", "ANEL"), _linha("B", "BICO"), _linha("C", "CANO"), _linha("Z", "ZERO", slot=0)]
    mestre = [{"codigo": "A", "produto": "ANEL", "qtd_sistema": 24},
              {"codigo": "B", "produto": "BICO", "qtd_sistema": 4},
              {"codigo": "C", "produto": "CANO", "qtd_sistema": 12}]
    end = [{"produto_codigo": "A", "enderecado": 18},
           {"produto_codigo": "B", "enderecado": 6},
           {"produto_codigo": "C", "enderecado": 12}]
    assert dd.saldos_das_caixas(est, mestre, {}, end) == {"A": "falta", "B": "sobra", "C": "ok"}
    # Sem estoque_mestre ou sem endereçado, não afirma saldo nenhum.
    assert dd.saldos_das_caixas(est, None, {}, end) == {}
    assert dd.saldos_das_caixas(est, mestre, {}, None) == {}


def test_loja_de_exemplo_nao_inventa_caixa_mista_e_mostra_a_de_demonstracao():
    loja = dd.loja_exemplo()
    mistas = [cx for i in loja["itens"] for cx in i["mistas"]]
    assert len(mistas) == 1
    assert mistas[0]["nome"] == "Peças Hoppner" and len(mistas[0]["pr"]) == 3
