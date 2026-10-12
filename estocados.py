"""Produtos estocados (material de cooperado guardado na CAMDA).

Porte de LeoLira1/Gondolas: lib/estocados_busca.dart. A lista vem de
`materiais_terceiros`. Esse material já foi faturado e saiu do sistema, então
NADA dele entra no saldo (estoque_localizado, baixa pela contagem, conferência).

Regra central: o palete de estocado tem `produto_codigo` começando por "EST:".
O Gondolas não espelha esses paletes em `estoque_localizado` e o código não casa
com nenhuma linha de `estoque_mestre`. Este app só lê, mas aplica a mesma regra
ao montar saldos, e `deve_espelhar` fica pronta para qualquer escrita futura.

Sem Streamlit e sem rede, para poder ser testado.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

PREFIXO_ESTOCADO = "EST:"
COR_ESTOCADO = "#8B5CF6"  # violeta, para não se confundir com nenhuma categoria da loja

SQL_ESTOCADOS = (
    "SELECT * FROM materiais_terceiros WHERE saldo > 0 ORDER BY razao_social, descricao"
)


def codigo_eh_estocado(codigo: str | None) -> bool:
    return (codigo or "").startswith(PREFIXO_ESTOCADO)


def deve_espelhar(codigo: str | None) -> bool:
    """False para "EST:": quem escrever em galpao_racks/barracao_enderecos NÃO grava em estoque_localizado."""
    return not codigo_eh_estocado(codigo)


@dataclass(frozen=True)
class ItemEstocado:
    cooperado: str
    produto: str
    codigo: str
    armazem: str
    documento: str
    emissao: str
    saldo: float

    @property
    def nome_do_palete(self) -> str:
        """Texto gravado em `produto_nome`: chave que liga o palete ao item (o código sozinho não serve,
        dois cooperados podem ter o mesmo produto)."""
        return f"{self.produto} · {self.cooperado}"

    @property
    def codigo_do_palete(self) -> str:
        return f"{PREFIXO_ESTOCADO}{self.codigo or self.produto}"


def _texto(linha: dict[str, Any], nomes: Iterable[str]) -> str:
    for n in nomes:
        v = linha.get(n)
        v = "" if v is None else str(v)
        if v:
            return v
    return ""


def item_de_linha(linha: dict[str, Any]) -> ItemEstocado:
    """Lê a linha de materiais_terceiros tolerando os mesmos sinônimos de coluna do app Estocados."""
    l = {str(k).lower(): v for k, v in linha.items()}
    saldo_txt = _texto(l, ["saldo"]).replace(",", ".")
    try:
        saldo = float(saldo_txt)
    except ValueError:
        saldo = 0.0
    return ItemEstocado(
        cooperado=_texto(l, ["razao_social", "cooperado", "cliente"]),
        produto=_texto(l, ["descricao", "produto", "descricao_produto"]),
        codigo=_texto(l, ["codigo", "cod", "codigo_produto", "cod_produto", "produto_codigo"]),
        armazem=_texto(l, ["armazem", "arm", "cod_armazem", "codigo_armazem"]),
        documento=_texto(l, ["documento", "doc", "num_doc", "numero_documento", "nota", "num_nota"]),
        emissao=_texto(l, ["emissao", "data_emissao", "dt_emissao", "data", "data_entrada"]),
        saldo=saldo,
    )


def _normalizar(s: str) -> str:
    decomposto = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def buscar_estocados(query: str, itens: list[ItemEstocado]) -> list[ItemEstocado]:
    """Cada termo (separado por espaço) precisa aparecer no cooperado, no produto OU no código.
    Sem acento e sem maiúscula. Consulta vazia devolve tudo."""
    termos = [t for t in re.split(r"\s+", _normalizar(query.strip())) if t]
    if not termos:
        return list(itens)
    saida = []
    for i in itens:
        alvo = _normalizar(f"{i.cooperado} {i.produto} {i.codigo}")
        if all(t in alvo for t in termos):
            saida.append(i)
    return saida


def enderecos_dos_estocados(
    galpao: Iterable[dict[str, Any]], barracao: Iterable[dict[str, Any]]
) -> dict[str, list[str]]:
    """Endereços por nome de palete, só dos paletes "EST:".

    galpao: {posicao, ordem, codigo, nome}; barracao: {rotulo, codigo, nome}.
    """
    mapa: dict[str, list[str]] = {}
    for r in galpao:
        if codigo_eh_estocado(r["codigo"]):
            mapa.setdefault(r["nome"], []).append(f"Galpão {r['posicao']} · N{r['ordem']}")
    for e in barracao:
        if codigo_eh_estocado(e["codigo"]):
            mapa.setdefault(e["nome"], []).append(e["rotulo"])
    return mapa


def resumo_ocupacao(total_vagas: int, codigos: Iterable[str]) -> str:
    """"38 livres · 30 estocados · 61 loja": parte zerada some (livres sempre aparece).
    `codigos` são os códigos de TODOS os racks ocupados."""
    estocados = loja = 0
    for c in codigos:
        if codigo_eh_estocado(c):
            estocados += 1
        else:
            loja += 1
    livres = total_vagas - estocados - loja
    partes = [f"{livres} livres"]
    if estocados:
        partes.append(f"{estocados} estocados")
    if loja:
        partes.append(f"{loja} loja")
    return " · ".join(partes)


def catalogo_da_cena(catalogo: dict[str, str], estocados: Iterable[tuple[str, str]]) -> list[dict[str, Any]]:
    """Catálogo de busca das cenas: um item por código da loja e UM POR COOPERADO nos estocados
    (`e: True`), porque dois cooperados com o mesmo produto repartem o mesmo código "EST:"."""
    itens: list[dict[str, Any]] = [{"c": c, "n": n} for c, n in sorted(catalogo.items())]
    itens += [{"c": c, "n": n, "e": True} for c, n in sorted(set(estocados))]
    return itens


def para_cena(linhas: list[dict[str, Any]] | None, galpao_racks: Iterable[dict[str, Any]],
              barracao_pal: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """JSON da lista de estocados para as cenas, já com os endereços de cada item.

    `linhas` = materiais_terceiros (None quando a tabela não pôde ser lida).
    """
    enderecos = enderecos_dos_estocados(
        [{"posicao": p, "ordem": r["o"], "codigo": r["c"], "nome": r["nome"]} for p, r in galpao_racks],
        [{"rotulo": e["rot"], "codigo": e["c"], "nome": e["n"]} for e in barracao_pal],
    )
    # Várias linhas do mesmo produto do mesmo cooperado (lotes, notas) viram UM item, com o saldo somado.
    # A chave é o nome do palete (PRODUTO · COOPERADO), a mesma que liga o palete ao item.
    por_nome: dict[str, dict[str, Any]] = {}
    for linha in linhas or []:
        i = item_de_linha(linha)
        if i.saldo <= 0:
            continue
        item = por_nome.get(i.nome_do_palete)
        if item is None:
            por_nome[i.nome_do_palete] = {
                "coop": i.cooperado, "prod": i.produto, "cod": i.codigo, "arm": i.armazem, "doc": i.documento,
                "saldo": i.saldo, "n": 1, "nome": i.nome_do_palete, "codp": i.codigo_do_palete,
                "end": enderecos.get(i.nome_do_palete, []),
            }
        else:
            item["saldo"] += i.saldo
            item["n"] += 1
    itens = list(por_nome.values())
    return {"ok": linhas is not None, "itens": itens, "cor": COR_ESTOCADO}
