"""Mapa 3D do galpão da CAMDA — cópia web, SOMENTE LEITURA, do app Gondolas.

Python lê o Turso (token em st.secrets) e injeta na cena só um JSON de dados;
o token nunca chega ao navegador.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import dados as dd

ALTURA_MAPA = 780
UI_CSS = Path(__file__).with_name("ui.css")
UI_JS = Path(__file__).with_name("ui.js")
CENAS = {"galpao": Path(__file__).with_name("cena.html"), "loja": Path(__file__).with_name("cena_loja.html"),
         "barracao": Path(__file__).with_name("cena_barracao.html")}

st.set_page_config(page_title="CAMDA · Mapas 3D", page_icon="📦", layout="wide")
st.markdown(
    """
<style>
.block-container { padding: 2.4rem 1.4rem 1.2rem; max-width: 1500px; }
footer, [data-testid="stDecoration"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.brand { display: flex; align-items: center; gap: .75rem; }
.brand .logo { width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #f08a3c, #e87722);
  color: #fff; display: grid; place-items: center; font-size: 1.25rem; box-shadow: 0 6px 16px rgba(232,119,34,.35); }
.brand h1 { font-size: 1.35rem; line-height: 1.15; margin: 0; padding: 0; font-weight: 700; letter-spacing: -.01em; }
.brand small { color: #8a877f; font-size: .78rem; }
.stats { display: flex; flex-wrap: wrap; gap: .5rem; margin: .9rem 0 .8rem; }
.stat { background: #fff; border: 1px solid #e3dfd5; border-radius: 999px; padding: .3rem .8rem; font-size: .84rem; color: #5d5a53;
  box-shadow: 0 1px 2px rgba(60,50,30,.04); white-space: nowrap; }
.stat b { color: #2b2a27; font-weight: 700; }
.stat .d { display: inline-block; width: .55rem; height: .55rem; border-radius: 50%; margin-right: .45rem; vertical-align: .05rem; }
.stat.pct { padding-left: .6rem; }
.stat.pct .barra { display: inline-block; width: 3.2rem; height: .5rem; border-radius: 999px; background: #ece8de; margin-right: .5rem; vertical-align: .08rem; overflow: hidden; }
.stat.pct .barra i { display: block; height: 100%; background: linear-gradient(90deg, #f08a3c, #e87722); border-radius: 999px; }
.stat.demo { background: #fff4e8; border-color: #f3c89c; color: #a4570f; }
.stat.hora { margin-left: auto; background: transparent; border-color: transparent; box-shadow: none; color: #8a877f; }
iframe { border-radius: 18px; border: 1px solid #e3dfd5 !important; box-shadow: 0 14px 40px rgba(60,50,30,.14); background: #eeebe4; }
[data-testid="stSegmentedControl"] button, [data-testid="stRadio"] label { font-weight: 600; }
[data-testid="stAlert"] { border-radius: 14px; }
@media (max-width: 760px) { .block-container { padding: 2.2rem .8rem 1rem; } .brand h1 { font-size: 1.15rem; } .stat.hora { margin-left: 0; } }
</style>
""",
    unsafe_allow_html=True,
)


def _segredo(nome: str) -> str | None:
    try:
        valor = st.secrets[nome]
    except Exception:  # sem secrets.toml, ou chave ausente
        valor = os.environ.get(nome)
    return str(valor).strip() if valor else None


@st.cache_data(ttl=60, show_spinner="Lendo o Turso…")
def ler_banco(url: str, token: str) -> tuple[dict, str]:
    """Lê os três mapas de uma vez (a busca é global). Só é cacheado quando dá certo."""
    return dd.ler_tudo(url, token), datetime.now().strftime("%H:%M:%S")


def carregar() -> tuple[dict, str | None, str | None]:
    """(dados dos três mapas, hora da leitura, motivo do fallback). Motivo != None → dados de exemplo."""
    url, token = _segredo("TURSO_URL"), _segredo("TURSO_TOKEN")
    if not url or not token:
        return dd.tudo_exemplo(), None, "TURSO_URL / TURSO_TOKEN não configurados em st.secrets"
    try:
        tudo, hora = ler_banco(url, token)
        return tudo, hora, None
    except dd.TursoErro as e:
        return dd.tudo_exemplo(), None, str(e)
    except Exception as e:  # resposta inesperada: nunca vaza URL nem token
        return dd.tudo_exemplo(), None, f"erro ao ler o Turso ({type(e).__name__})"


def cena_html(dados: dict, mapa: str, indice: list) -> str:
    # a cena recebe o índice global de produtos e qual mapa ela é (busca em todos os mapas)
    dados = {**dados, "global": indice, "area": mapa}
    # `</` quebraria o <script>; U+2028/2029 quebram strings JS antigas.
    payload = (
        json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )
    html = CENAS[mapa].read_text(encoding="utf-8")
    html = html.replace("/*__UI_CSS__*/", UI_CSS.read_text(encoding="utf-8"), 1)
    html = html.replace("/*__UI_JS__*/", UI_JS.read_text(encoding="utf-8"), 1)
    return html.replace("/*__DADOS__*/null", payload, 1)


# ── Página ──────────────────────────────────────────────────────────────────
MAPAS = {"Galpão": "galpao", "Loja": "loja", "Barracão": "barracao"}

c_marca, c_mapa, c_btn = st.columns([3, 4, 1.2], vertical_alignment="center")
c_marca.markdown(
    '<div class="brand"><div class="logo">📦</div><div><h1>CAMDA · Mapas 3D</h1>'
    "<small>Somente leitura · Quirinópolis-GO</small></div></div>",
    unsafe_allow_html=True,
)
if hasattr(st, "segmented_control"):
    escolha = c_mapa.segmented_control("Mapa", list(MAPAS), default="Galpão", label_visibility="collapsed") or "Galpão"
else:
    escolha = c_mapa.radio("Mapa", list(MAPAS), horizontal=True, label_visibility="collapsed")
mapa = MAPAS[escolha]
tudo, hora, motivo = carregar()
dados = tudo[mapa]
motivo = motivo or tudo["erros"].get(mapa)

with c_btn:
    if st.button("↻ Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def _pct(rotulo: str, pct: int, dica: str = "") -> str:
    """Indicador de ocupação: barrinha + porcentagem."""
    return (f'<span class="stat pct" title="{dica}"><span class="barra"><i style="width:{min(pct, 100)}%"></i></span>'
            f"<b>{pct}%</b> {rotulo}</span>")


def _stat(rotulo: str, valor: object, cor: str | None = None) -> str:
    ponto = f'<span class="d" style="background:{cor}"></span>' if cor else ""
    return f'<span class="stat">{ponto}<b>{valor}</b> {rotulo}</span>'


if mapa == "galpao":
    pilhas = dados["pilhas"]
    total = len(dados["posicoes"])
    falta = sum(1 for d in dados["divergencia"].values() if d["t"] == "falta")
    sobra = sum(1 for d in dados["divergencia"].values() if d["t"] == "sobra")
    oc = dd.ocupacao_galpao(dados)
    chips = [
        _pct("ocupado", oc["vagas"], f"Vagas ocupadas: {len(pilhas)} de {total} posições têm ao menos um rack"),
        _pct("da capacidade", oc["capacidade"], f"Racks ÷ capacidade ({total} posições × {dados['geo']['niveisMax']} níveis)"),
        _stat(f"de {total} posições com carga", len(pilhas)),
        _stat("livres", total - len(pilhas)),
        _stat("racks", sum(len(p) for p in pilhas.values())),
        _stat("produtos com carga sem endereço", falta, "#e53935"),
        _stat("endereçados além do sistema", sobra, "#1565C0"),
    ]
elif mapa == "barracao":
    pal = dados["pal"]
    ocupados = [p for p in pal if p["c"].strip()]
    chips = [
        _pct("ocupado", dd.ocupacao_barracao(dados), f"Paletes com bag: {len(ocupados)} de {len(pal)}"),
        _stat(f"de {len(pal)} paletes com bag", len(ocupados), "#c99d66"),
        _stat("livres", len(pal) - len(ocupados)),
        _stat("unidades", f"{sum(p['q'] for p in ocupados):g}"),
        _stat("produtos", len(dados["catalogo"])),
        _stat(f"fileiras · corredor de {dados['corredor']:g} m", dados["fileiras"]),
    ]
else:
    itens = [i for i in dados["itens"] if i["kind"] != "balcao"]
    chips = [
        _pct("com produto", dd.ocupacao_loja(dados), "Estruturas com ao menos um produto endereçado"),
        _stat("estruturas", len(itens), "#4caf50"),
        _stat("com produto endereçado", sum(1 for i in itens if i["prod"])),
        _stat("produtos", len(dados["catalogo"])),
    ]
if motivo:
    chips.append('<span class="stat demo">dados de exemplo</span>')
elif hora:
    chips.append(f'<span class="stat hora">↻ lido às {hora} · cache de 60 s</span>')
st.markdown('<div class="stats">' + "".join(chips) + "</div>", unsafe_allow_html=True)

if motivo:
    st.warning(f"Mostrando DADOS DE EXEMPLO — {motivo}.", icon="⚠️")
for aviso in dados.get("avisos", []):
    st.info(aviso)

html_cena = cena_html(dados, mapa, dd.indice_global(tudo["galpao"], tudo["loja"], tudo["barracao"]))
if hasattr(st, "iframe"):
    # components.v1.html está marcado para remoção nas versões novas do Streamlit
    st.iframe(html_cena, height=ALTURA_MAPA)
else:
    components.html(html_cena, height=ALTURA_MAPA, scrolling=False)
