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
