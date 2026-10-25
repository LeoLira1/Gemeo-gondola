"""Planta e regras do galpão de racks da CAMDA.

Porte direto de LeoLira1/Gondolas (lib/galpao_config.dart, lib/galpao_saldo.dart
e lib/codigos_vinculados.dart). Os números abaixo são os do app Flutter: se a
planta for remedida, o ajuste é feito LÁ e copiado para cá.

Sem Streamlit e sem rede, para poder ser testado.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

# ── Medidas do rack (metros) ────────────────────────────────────────────────
COMPRIMENTO_RACK = 1.20   # lado que corre ao longo da rua
LARGURA_RACK = 1.00       # lado atravessado à rua
ALTURA_NIVEL = 1.10
PASSO_POSICAO = 1.34      # rack (1,20) + folga
PASSO_NIVEL = 1.16        # altura (1,10) + encaixe
NIVEIS_MAX = 4
PARTES = (1, 2)


@dataclass(frozen=True)
class Rua:
    numero: int
    parte: int
    eixo: str            # 'x' ou 'z': eixo ao longo do qual as posições se sucedem
    coord_fixa: float
    centro: float
    quantidade: int
    primeiro_numero: int
    primeiro_no_fim: bool
    lado_corredor: int

    @property
    def ultimo_numero(self) -> int:
        return self.primeiro_numero + self.quantidade - 1

    def contem(self, numero: int) -> bool:
        return self.primeiro_numero <= numero <= self.ultimo_numero


# Tabela das ruas — GalpaoConfig.ruas.
RUAS: tuple[Rua, ...] = (
    # Parte 1 — 8 ruas, 85 posições (1–85)
    Rua(1, 1, "z", 8.30, 1.00, 14, 1, True, -1),
    Rua(2, 1, "x", -9.30, 0.50, 11, 15, True, 1),
    Rua(3, 1, "z", -7.60, 0, 11, 26, False, 1),
    Rua(4, 1, "z", -2.90, 0, 10, 37, False, -1),
    Rua(5, 1, "z", -1.85, 0, 10, 47, False, 1),
    Rua(6, 1, "z", 2.60, 0, 11, 57, True, -1),
    Rua(7, 1, "z", 3.65, 0, 11, 68, False, 1),
    Rua(8, 1, "x", 11.30, -2.18, 7, 79, False, -1),
    # Parte 2 — 4 ruas de 11 (86–129), serpentina
    Rua(9, 2, "z", 29.35, 0, 11, 86, False, -1),
    Rua(10, 2, "z", 24.90, 0, 11, 97, True, -1),
    Rua(11, 2, "z", 20.45, 0, 11, 108, False, -1),
    Rua(12, 2, "z", 16.00, 0, 11, 119, True, -1),
)


@dataclass(frozen=True)
class Posicao:
    numero: int
    rua: Rua
    x: float
    z: float

    @property
    def parte(self) -> int:
        return self.rua.parte

    @property
    def tamanho_x(self) -> float:
        return LARGURA_RACK if self.rua.eixo == "z" else COMPRIMENTO_RACK

    @property
    def tamanho_z(self) -> float:
        return COMPRIMENTO_RACK if self.rua.eixo == "z" else LARGURA_RACK


def _montar_posicoes() -> tuple[Posicao, ...]:
    lista: list[Posicao] = []
    for rua in RUAS:
        for i in range(rua.quantidade):
            desloc = (i - (rua.quantidade - 1) / 2) * PASSO_POSICAO
            ordinal = rua.quantidade - 1 - i if rua.primeiro_no_fim else i
            lista.append(
                Posicao(
                    numero=rua.primeiro_numero + ordinal,
                    rua=rua,
                    x=rua.coord_fixa if rua.eixo == "z" else rua.centro + desloc,
                    z=rua.centro + desloc if rua.eixo == "z" else rua.coord_fixa,
                )
            )
    lista.sort(key=lambda p: p.numero)
    return tuple(lista)


POSICOES: tuple[Posicao, ...] = _montar_posicoes()
POSICAO_POR_NUMERO: dict[int, Posicao] = {p.numero: p for p in POSICOES}
TOTAL_POSICOES = len(POSICOES)


def y_base(ordem: int) -> float:
    """Altura do piso do rack de ordem `ordem` (1 = o de baixo)."""
    return (ordem - 1) * PASSO_NIVEL


# ── Códigos que são o MESMO produto (codigos_vinculados.dart) ──────────────

_ESPACOS = re.compile(r"\s+")


def chave_nome_produto(texto: str) -> str:
    """Maiúsculo, sem acento, espaços colapsados. Mesma chave do app do scanner."""
    cru = (texto or "").strip().upper()
    decomposto = unicodedata.normalize("NFD", cru)
    sem_marcas = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _ESPACOS.sub(" ", sem_marcas).strip()


def normalizar_codigo(codigo: str | None) -> str | None:
    if codigo is None:
        return None
    texto = str(codigo).strip().upper()
    return texto or None


def grupos_de_codigos(
    codigos,
    produto_id_por_codigo: dict[str, str],
    nome_por_codigo: dict[str, str],
) -> dict[str, set[str]]:
    """Para cada código, o conjunto de códigos que somam com ele.

    1. Cadastro (mapa_produtos + mapa_produtos_codigos): vinculado a um
       produto_id, o grupo são os códigos daquele produto_id.
    2. Sem vínculo, o NOME: mesma chave de nome, ignorando quem já tem vínculo.
    O grupo sempre contém o próprio código.
    """
    por_produto_id: dict[str, str] = {}
    codigos_do_produto: dict[str, set[str]] = {}
    for codigo, produto_id in produto_id_por_codigo.items():
        c = normalizar_codigo(codigo)
        p = str(produto_id).strip()
        if c is None or not p:
            continue
        por_produto_id[c] = p
        codigos_do_produto.setdefault(p, set()).add(c)

    nomes: dict[str, str] = {}
    for codigo, nome in nome_por_codigo.items():
        c = normalizar_codigo(codigo)
        if c is not None:
            nomes[c] = nome

    chave_por_codigo: dict[str, str] = {}
    codigos_por_chave: dict[str, set[str]] = {}
    for codigo, nome in nomes.items():
        if codigo in por_produto_id:
            continue
        chave = chave_nome_produto(nome)
        if not chave:  # nome em branco não junta nada
            continue
        chave_por_codigo[codigo] = chave
        codigos_por_chave.setdefault(chave, set()).add(codigo)

    grupos: dict[str, set[str]] = {}
    for bruto in codigos:
        codigo = normalizar_codigo(bruto)
        if codigo is None or codigo in grupos:
            continue
        produto_id = por_produto_id.get(codigo)
        if produto_id is not None:
            grupos[codigo] = {codigo} | codigos_do_produto.get(produto_id, set())
            continue
        chave = chave_por_codigo.get(codigo)
        grupos[codigo] = {codigo} if chave is None else {codigo} | codigos_por_chave[chave]
    return grupos


# ── Saldo sistema × endereçado (galpao_saldo.dart) ─────────────────────────

TOLERANCIA = 0.001


@dataclass(frozen=True)
class Saldo:
    codigo: str
    qtd_sistema: float
    enderecado: float
    codigos_somados: tuple[str, ...] = ()

    @property
    def diferenca(self) -> float:
        return self.enderecado - self.qtd_sistema

    @property
    def falta(self) -> bool:
        """Carga do sistema sem endereço → rack VERMELHO."""
        return self.diferenca < -TOLERANCIA

    @property
    def sobra(self) -> bool:
        """Endereçado além do sistema → rack AZUL."""
        return self.diferenca > TOLERANCIA


def montar_saldos(
    codigos,
    grupos: dict[str, set[str]],
    sistema_por_codigo: dict[str, float],
    enderecado_por_codigo: dict[str, float],
) -> dict[str, Saldo]:
    """Saldo por código (chave = código como está em galpao_racks).

    Soma TODOS os códigos do grupo nos dois lados. Produto sem NENHUMA linha
    em estoque_mestre fica de fora: sem qtd_sistema não há saldo a afirmar.
    """
    saldos: dict[str, Saldo] = {}
    for bruto in codigos:
        codigo = normalizar_codigo(bruto)
        if codigo is None or bruto in saldos:
            continue
        grupo = sorted(grupos.get(codigo, {codigo}))
        if not any(c in sistema_por_codigo for c in grupo):
            continue
        sistema = sum(sistema_por_codigo.get(c, 0.0) for c in grupo)
        enderecado = sum(enderecado_por_codigo.get(c, 0.0) for c in grupo)
        saldos[bruto] = Saldo(bruto, sistema, enderecado, tuple(grupo))
    return saldos


# ── Escada para o mesanino (referência, não é endereço) ─────────────────────
# Fica no Galpão Parte 1, paralela à Rua 1, do lado oposto ao corredor (o lado da parede). A base fica
# junto ao nº 14 e a escada sobe no sentido decrescente da numeração, até o nº 11, terminando na
# altura do 3º nível (topo do rack N3, palete incluído). Posição e altura vêm das posições da planta;
# largura e folga são estimativas (ajustar aqui quando medir).
PALETE_ALTURA = 0.12
ESCADA_PARTE = 1
ESCADA_DE, ESCADA_ATE = 14, 11
ESCADA_LARGURA = 0.90
ESCADA_FOLGA = 0.12        # entre a lateral do rack e a escada
ESCADA_PATAMAR = 0.90      # plataforma no alto, antes do mesanino
ESCADA_NIVEL_TOPO = 3


def escada() -> dict:
    """Retângulo da escada no chão (metros), altura do topo e comprimento do patamar."""
    a, b = POSICAO_POR_NUMERO[ESCADA_DE], POSICAO_POR_NUMERO[ESCADA_ATE]
    lado = 1 if a.rua.lado_corredor < 0 else -1            # oposto ao corredor
    borda = a.x + lado * (a.tamanho_x / 2 + ESCADA_FOLGA)
    x0, x1 = sorted((borda, borda + lado * ESCADA_LARGURA))
    z_a, z_b = a.z, b.z
    sentido = 1 if z_b > z_a else -1                       # a escada sobe do 14 para o 11
    z_ini = z_a - sentido * a.tamanho_z / 2                # ponta do 14 (base)
    z_fim = z_b + sentido * b.tamanho_z / 2                # ponta do 11 (topo)
    return {
        "parte": ESCADA_PARTE, "de": ESCADA_DE, "ate": ESCADA_ATE,
        "x0": round(x0, 4), "x1": round(x1, 4), "z0": round(z_ini, 4), "z1": round(z_fim, 4),
        "sentido": sentido,
        "altura": round(PALETE_ALTURA + (ESCADA_NIVEL_TOPO - 1) * PASSO_NIVEL + ALTURA_NIVEL, 4),
        "patamar": ESCADA_PATAMAR,
        "lado": lado,
    }


# ── Chuveiro lava-olhos (equipamento de emergência, referência) ─────────────
# Fica na Parte 1, alinhado à Rua 2 e além do nº 25 (a oeste, na ponta da fileira), no ponto marcado no
# desenho. A altura máxima é a de 2 níveis (palete + 2 racks). A distância até o nº 25 é estimativa.
LAVA_OLHOS_PARTE = 1
LAVA_OLHOS_REFERENCIA = 25
LAVA_OLHOS_RECUO = 1.20          # da lateral do nº 25 até o pé do chuveiro (mais para dentro, para a parede chegar perto)
LAVA_OLHOS_NIVEIS = 2


def lava_olhos() -> dict:
    p = POSICAO_POR_NUMERO[LAVA_OLHOS_REFERENCIA]
    return {
        "parte": LAVA_OLHOS_PARTE,
        "x": round(p.x - p.tamanho_x / 2 - LAVA_OLHOS_RECUO, 4),
        "z": round(p.z, 4),
        "altura": round(PALETE_ALTURA + (LAVA_OLHOS_NIVEIS - 1) * PASSO_NIVEL + ALTURA_NIVEL, 4),
        "niveis": LAVA_OLHOS_NIVEIS,
        "rua": p.rua.numero,
    }


# ── Mesa de expedição com gaveteiro (referência, não é endereço) ────────────
# Fica no Galpão Parte 2, na ponta da Rua 12, além do nº 119 (no ponto marcado no desenho). Mesa reta com as
# duas laterais em painel cheio (nenhum pé de ferro) e painel de fundo; o gaveteiro (2 gavetas + 1 de pasta)
# fica embaixo do tampo, encostado na lateral do lado do 119, avançando um pouco à frente. A frente dá para o leste, o corredor da Rua 11.
# Medidas do modelo; o recuo é estimativa.
MESA_PARTE = 2
MESA_REFERENCIA = 119
MESA_RECUO = 0.60            # da ponta do nº 119 até a lateral da mesa
MESA_COMPRIMENTO = 1.50
MESA_PROFUNDIDADE = 0.70
MESA_ALTURA = 0.75
GAVETEIRO_LARGURA = 0.45
GAVETEIRO_PROFUNDIDADE = 0.55
GAVETEIRO_ALTURA = 0.68
GAVETEIRO_FOLGA = 0.01       # entre a lateral da mesa e o gaveteiro (por dentro)
GAVETEIRO_AVANCO = 0.06      # a frente do gaveteiro passa um pouco da frente da mesa


def mesa() -> dict:
    """Mesa no chão (metros). `z_ini` é a ponta do lado do 119 (a do gaveteiro), `sentido` aponta
    para a ponta livre; `x_fundo` é o fundo da mesa e `frente` o lado para onde ela olha."""
    p = POSICAO_POR_NUMERO[MESA_REFERENCIA]
    ps = [q for q in POSICOES if q.rua is p.rua]
    sentido = 1 if p.z >= max(q.z for q in ps) else -1        # para fora da fileira
    z_ini = p.z + sentido * (p.tamanho_z / 2 + MESA_RECUO)
    frente = -p.rua.lado_corredor                             # o corredor da própria rua fica atrás
    x_fundo = p.x - frente * p.tamanho_x / 2                   # fundo alinhado à face do rack
    comp_total = MESA_COMPRIMENTO                              # o gaveteiro fica embaixo do tampo
    prof_total = max(MESA_PROFUNDIDADE, MESA_PROFUNDIDADE + GAVETEIRO_AVANCO)
    xs = sorted((x_fundo, x_fundo + frente * prof_total))
    zs = sorted((z_ini, z_ini + sentido * comp_total))
    return {
        "parte": MESA_PARTE, "ref": MESA_REFERENCIA, "rua": p.rua.numero,
        "x_fundo": round(x_fundo, 4), "frente": frente,
        "z_ini": round(z_ini, 4), "sentido": sentido,
        "x0": round(xs[0], 4), "x1": round(xs[1], 4), "z0": round(zs[0], 4), "z1": round(zs[1], 4),
        "comprimento": MESA_COMPRIMENTO, "profundidade": MESA_PROFUNDIDADE, "altura": MESA_ALTURA,
        "comprimento_total": round(comp_total, 4),
        "gaveteiro": {"largura": GAVETEIRO_LARGURA, "profundidade": GAVETEIRO_PROFUNDIDADE, "altura": GAVETEIRO_ALTURA,
                      "folga": GAVETEIRO_FOLGA, "avanco": GAVETEIRO_AVANCO, "gavetas": 3},
    }


# ── Empilhadeira patolada (referência, modelo 3D) ───────────────────────────
# Fica estacionada em frente à mesa de expedição, no corredor da Rua 11, paralela à mesa: a traseira (timão) junto
# à ponta livre da mesa, onde o piso termina (frente aberta do Galpão 2), e o garfo apontando para dentro do galpão.
# Fica no trecho plano, antes da rampa (RAMPA.x0 = 17,5 m em cena.html). O modelo é o vehicle_forklift_orange_a01
# da NVIDIA SimReady (static/modelos/, CC BY 4.0). No arquivo, o garfo aponta para +Z e a origem fica no chão; as
# medidas abaixo são as do modelo. As folgas são estimativas.
EMPILHADEIRA_MODELO = "app/static/modelos/vehicle_forklift_orange_a01.glb"
EMPILHADEIRA_LARGURA = 0.82
EMPILHADEIRA_TRAS = 0.35       # da origem até a traseira (timão)
EMPILHADEIRA_FRENTE = 1.53     # da origem até a ponta do garfo
EMPILHADEIRA_ALTURA = 1.97
EMPILHADEIRA_FOLGA = 0.30      # da frente da mesa até a lateral da empilhadeira
EMPILHADEIRA_RECUO = 0.10      # da borda do piso (ponta livre da mesa) até a traseira


def empilhadeira() -> dict:
    """Posição da empilhadeira (metros): `x`, `z` da origem do modelo, `rot` em torno de Y e a caixa no chão."""
    m = mesa()
    sentido, frente = m["sentido"], m["frente"]
    borda = m["z_ini"] + sentido * m["comprimento_total"]          # ponta livre da mesa = fim do piso
    z_tras = borda - sentido * EMPILHADEIRA_RECUO
    z = z_tras - sentido * EMPILHADEIRA_TRAS
    x_frente_mesa = m["x1"] if frente > 0 else m["x0"]
    x = x_frente_mesa + frente * (EMPILHADEIRA_FOLGA + EMPILHADEIRA_LARGURA / 2)
    zs = sorted((z_tras, z - sentido * EMPILHADEIRA_FRENTE))
    return {
        "parte": m["parte"], "rua": m["rua"], "modelo": EMPILHADEIRA_MODELO,
        "x": round(x, 4), "z": round(z, 4), "rot": round(math.pi, 6) if sentido > 0 else 0.0,   # garfo para dentro
        "x0": round(x - EMPILHADEIRA_LARGURA / 2, 4), "x1": round(x + EMPILHADEIRA_LARGURA / 2, 4),
        "z0": round(zs[0], 4), "z1": round(zs[1], 4),
        "largura": EMPILHADEIRA_LARGURA, "comprimento": EMPILHADEIRA_TRAS + EMPILHADEIRA_FRENTE,
        "altura": EMPILHADEIRA_ALTURA,
    }
