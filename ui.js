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
  n.className = "btn"; n.id = "bRot"; n.title = "Mostrar os números sobre as estruturas (começa desligado)";
  // Começa SEM rótulos; o botão liga. A escolha acompanha a troca de aba (sessionStorage, só nesta aba do navegador).
  const ligar = (on) => {
    window.__rotulosOn = on; n.textContent = on ? "Rótulos ✓" : "Rótulos"; n.classList.toggle("on", on); dirty = true;
    try { sessionStorage.setItem("camda_rotulos", on ? "1" : "0"); } catch (e) {}
  };
  n.onclick = () => ligar(!window.__rotulosOn);
  let inicial = false;
  try { inicial = sessionStorage.getItem("camda_rotulos") === "1"; } catch (e) {}
  ligar(inicial);
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

// ── Produtos estocados (material de cooperado), galpão e barracão ───────────
// Lista de materiais_terceiros com o endereço de cada item (já ligado pelo Python via "PRODUTO · COOPERADO").
// É material já faturado: fica FORA do saldo. Aqui é só consulta.
(function () {
  if (typeof D === "undefined" || !D.estocados || (D.area !== "galpao" && D.area !== "barracao")) return;
  const wrap = document.getElementById("wrap"), msg = document.getElementById("msg");
  const linha = (document.getElementById("qProd") || {}).closest ? document.getElementById("qProd").closest(".row") : null;
  const dobra = (s) => (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmtN = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  const itens = D.estocados.itens.map((i) => ({ ...i, k: dobra(`${i.coop} ${i.prod} ${i.cod}`) }));

  const painel = document.createElement("div");
  painel.id = "estoc"; painel.className = "panel"; painel.style.display = "none";
  painel.innerHTML = `<button class="x" title="Fechar">×</button><h4>Produtos estocados</h4>
    <div class="sub">Material de cooperado guardado na CAMDA · fora do saldo da loja</div>
    <input id="qEst" placeholder="cooperado, produto ou código" autocomplete="off"><div id="estLista"></div>`;
  wrap.appendChild(painel);

  function desenhar() {
    const termos = dobra($("qEst").value).trim().split(/\s+/).filter(Boolean);
    const achados = itens.filter((i) => termos.every((t) => i.k.includes(t)));
    const grupos = new Map();
    for (const i of achados) { if (!grupos.has(i.coop)) grupos.set(i.coop, []); grupos.get(i.coop).push(i); }
    let h = "";
    for (const [coop, lista] of grupos) {
      h += `<div class="coop">${esc(coop || "(sem cooperado)")}</div>`;
      for (const i of lista) {
        const onde = i.end.length ? "📍 " + i.end.map(esc).join(" · ") : "sem endereço";
        h += `<div class="it"><div>${esc(i.prod)}<br><span class="onde${i.end.length ? "" : " sem"}">${onde}</span></div><b>${fmtN.format(i.saldo)}</b></div>`;
      }
    }
    $("estLista").innerHTML = h || `<div class="sub">${D.estocados.ok ? "Nenhum item encontrado." : "materiais_terceiros indisponível."}</div>`;
  }
  const $ = (id) => document.getElementById(id);
  const b = document.createElement("button");
  b.className = "btn"; b.id = "bEst"; b.textContent = "Produtos estocados"; b.style.borderColor = D.estocados.cor;
  b.onclick = () => { const abrir = painel.style.display === "none"; painel.style.display = abrir ? "block" : "none"; b.classList.toggle("on", abrir); if (abrir) desenhar(); };
  painel.querySelector(".x").onclick = () => b.click();
  $("qEst").addEventListener("input", desenhar);
  (linha || $("top")).insertBefore(b, msg || null);

  // O campo Produto também procura nos estocados (cooperado, produto ou código), inclusive os sem endereço,
  // que nenhuma busca por palete enxerga. Acrescenta ao resumo da busca e abre o painel já filtrado.
  const campo = $("qProd");
  if (!campo || !msg) return;
  let t = null;
  campo.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => {                                   // depois do resumo da cena e do resumo global
      const termos = dobra(campo.value).trim().split(/\s+/).filter(Boolean);
      if (dobra(campo.value).trim().length < 2) return;
      const achados = itens.filter((i) => termos.every((x) => i.k.includes(x)));
      if (!achados.length) return;
      const sem = achados.filter((i) => !i.end.length).length;
      const coops = new Set(achados.map((i) => i.coop)).size;
      msg.insertAdjacentHTML("beforeend",
        ` · <a href="#" data-est="1" style="color:${D.estocados.cor}" title="Abrir a lista de estocados com esta busca">` +
        `Estocados ${achados.length} iten${achados.length === 1 ? "" : "s"}` +
        `${coops > 1 ? " de " + coops + " cooperados" : ""}${sem ? " (" + sem + " sem endereço)" : ""} →</a>`);
    }, 420);
  });
  msg.addEventListener("click", (ev) => {
    const a = ev.target.closest("a[data-est]");
    if (!a) return;
    ev.preventDefault();
    $("qEst").value = campo.value;
    if (painel.style.display === "none") b.click(); else desenhar();
  });
  if (campo.value) campo.dispatchEvent(new Event("input"));
})();
