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
