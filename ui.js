// Interface compartilhada: legenda recolhível e botão que oculta os rótulos numéricos.
(function () {
  const $$ = (id) => document.getElementById(id);
  const leg = $$("legend");
  if (leg) {
    const b = document.createElement("button");
    b.id = "bLeg"; b.className = "btn"; b.textContent = "Legenda";
    const abrir = (v) => { leg.classList.toggle("fechada", !v); b.classList.toggle("on", v); };
    abrir(window.innerWidth >= 1100);
    b.onclick = () => abrir(leg.classList.contains("fechada"));
    $$("wrap").appendChild(b);
  }
  const campo = $$("qProd");
  const linha = (campo && campo.closest(".row")) || $$("top");
  const n = document.createElement("button");
  n.className = "btn"; n.id = "bRot"; n.title = "Mostrar ou ocultar os números sobre as estruturas";
  const ligar = (on) => { window.__rotulosOn = on; n.textContent = "Rótulos"; n.classList.toggle("off", !on); dirty = true; };
  n.onclick = () => ligar(window.__rotulosOn === false);
  ligar(true);
  linha.insertBefore(n, $$("msg") || null);
})();

// ── Busca global: o produto é procurado no galpão, na loja e no barracão ─────
// O Python injeta em D.global uma linha por produto em cada local ({c, n, a: mapa, w: local}) e
// D.area (o mapa desta cena). Cada cena acende só o que é dela; aqui sai o resumo dos três mapas,
// com atalho para os outros, e a busca acompanha a pessoa ao trocar de aba.
(function () {
  const campo = document.getElementById("qProd"), msg = document.getElementById("msg");
  if (!campo || !msg || typeof D === "undefined" || !D.global) return;
  const NOMES = { galpao: "Galpão", loja: "Loja", barracao: "Barracão" };
  const dobra = (s) => (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const guardar = (v) => { try { sessionStorage.setItem("camda_busca", v); } catch (e) {} };

  function resumo(texto) {
    const q = dobra(texto).trim(), termos = q.length >= 2 ? q.split(/\s+/) : [];
    if (!termos.length) return "";
    const achados = D.global.filter((e) => termos.every((t) => dobra(e.n).includes(t) || dobra(e.c).includes(t)));
    if (!achados.length) return "nenhum produto em nenhum mapa";
    const produtos = new Set(achados.map((e) => e.c)).size, por = {};
    for (const e of achados) (por[e.a] ||= new Set()).add(e.w);
    const partes = Object.keys(NOMES).map((a) => {
      const n = por[a] ? por[a].size : 0;
      if (a === D.area) return `<b>${NOMES[a]} ${n}</b>`;
      return n ? `<a href="#" data-mapa="${a}" title="Abrir ${NOMES[a]} com esta busca">${NOMES[a]} ${n} →</a>` : `<span style="opacity:.55">${NOMES[a]} 0</span>`;
    });
    return `<b>${produtos}</b> produto${produtos > 1 ? "s" : ""} · ` + partes.join(" · ");
  }

  let t = null;
  campo.addEventListener("input", () => {
    guardar(campo.value);
    clearTimeout(t);
    t = setTimeout(() => { msg.innerHTML = resumo(campo.value); }, 340);   // depois do resumo próprio da cena
  });

  msg.addEventListener("click", (ev) => {
    const a = ev.target.closest("a[data-mapa]");
    if (!a) return;
    ev.preventDefault();
    guardar(campo.value);
    try {                                                                  // clica na aba do Streamlit (a cena é do mesmo domínio)
      const nome = NOMES[a.dataset.mapa], doc = window.parent.document;
      // o texto de cada aba é um <p>; o clique sobe até o botão do controle segmentado
      const alvo = [...doc.querySelectorAll('[data-testid="stSegmentedControl"] button, [data-testid="stRadio"] label, [data-testid="stMarkdownContainer"] p')]
        .find((el) => el.textContent.trim() === nome);
      if (alvo) { alvo.click(); return; }
    } catch (e) {}
    msg.insertAdjacentHTML("beforeend", ` <span style="opacity:.7">(abra a aba ${NOMES[a.dataset.mapa]})</span>`);
  });

  // ao abrir (ou ao trocar de aba), retoma a busca que estava valendo
  let inicial = "";
  try { inicial = sessionStorage.getItem("camda_busca") || ""; } catch (e) {}
  if (inicial) { campo.value = inicial; campo.dispatchEvent(new Event("input")); }
})();
