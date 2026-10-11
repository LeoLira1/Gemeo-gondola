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

ALTURA_MAPA = 700
CENA = Path(__file__).with_name("cena.html")

st.set_page_config(page_title="Galpão CAMDA", page_icon="📦", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:3rem;padding-bottom:1rem}</style>",
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
    """Lê o galpão. Só é cacheado quando dá certo (exceção não entra no cache)."""
    return dd.ler_turso(url, token), datetime.now().strftime("%H:%M:%S")


def carregar() -> tuple[dict, str | None, str | None]:
    """(dados, hora da leitura, motivo do fallback). Motivo != None → dados de exemplo."""
    url, token = _segredo("TURSO_URL"), _segredo("TURSO_TOKEN")
    if not url or not token:
        return dd.dados_exemplo(), None, "TURSO_URL / TURSO_TOKEN não configurados em st.secrets"
    try:
        dados, hora = ler_banco(url, token)
        return dados, hora, None
    except dd.TursoErro as e:
        return dd.dados_exemplo(), None, str(e)
    except Exception as e:  # resposta inesperada: nunca vaza URL nem token
        return dd.dados_exemplo(), None, f"erro ao ler o Turso ({type(e).__name__})"


def cena_html(dados: dict) -> str:
    # `</` quebraria o <script>; U+2028/2029 quebram strings JS antigas.
    payload = (
        json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )
    return CENA.read_text(encoding="utf-8").replace("/*__DADOS__*/null", payload, 1)


# ── Página ──────────────────────────────────────────────────────────────────
c_titulo, c_info, c_btn = st.columns([3, 5, 1], vertical_alignment="center")
c_titulo.subheader("Galpão CAMDA")
dados, hora, motivo = carregar()

with c_btn:
    if st.button("Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

pilhas = dados["pilhas"]
total = len(dados["posicoes"])
ocupadas = len(pilhas)
racks = sum(len(p) for p in pilhas.values())
falta = sum(1 for d in dados["divergencia"].values() if d["t"] == "falta")
sobra = sum(1 for d in dados["divergencia"].values() if d["t"] == "sobra")
c_info.caption(
    f"{ocupadas} de {total} posições com carga · {total - ocupadas} livres · {racks} racks · "
    f"{falta} produtos com carga sem endereço · {sobra} endereçados além do sistema"
    + (f" · lido às {hora} (cache de 60 s)" if hora else "")
)

if motivo:
    st.warning(f"Mostrando DADOS DE EXEMPLO — {motivo}.", icon="⚠️")
for aviso in dados.get("avisos", []):
    st.info(aviso)

html_cena = cena_html(dados)
if hasattr(st, "iframe"):
    # components.v1.html está marcado para remoção nas versões novas do Streamlit
    st.iframe(html_cena, height=ALTURA_MAPA)
else:
    components.html(html_cena, height=ALTURA_MAPA, scrolling=False)
