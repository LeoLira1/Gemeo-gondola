// ── Rack metálico empilhável com caixas 5L × 4 (Three.js r128) ──────────────
// Medidas do desenho técnico, em mm (RACK_MM). O rack é desenhado para caber numa "vaga" L × P × H em metros:
// L e P são a pegada (lado comprido e lado curto) e H a altura de empilhamento (base até a ponta da ponteira,
// onde apoia o rack de cima). As alturas do desenho (1750 mm) são reescaladas para H; a pegada usa L e P.
//
// Desempenho: tudo é InstancedMesh, uma instância por peça repetida. Um RackLote junta muitos racks em
// 8 malhas (montantes, ponteiras, travessas, chapas/moldura, madeira, caixas, bloco, sombra), então cada lote
// custa no máximo 8 draw calls (+1 no mapa de sombra), não importa quantos racks tenha. Cada rack entra no lote "perto" (modelo completo)
// ou "longe" (bloco com a textura de caixas + moldura). A cor do rack (saldo/busca) vai só na fita e na
// etiqueta das caixas: a estrutura é sempre metálica e o palete sempre madeira.
//
// Uso avulso: Rack3D.criarRack({ cor: 0x1565c0, camadas: 5, caixas: true }) → THREE.Group.
const Rack3D = (() => {
  const RACK_MM = {
    largura: 1200, profundidade: 1000, altura: 1750,     // pegada e altura de empilhamento (com a ponteira)
    palete: 145, tubo: 60, ponteira: 50,
    travessas: [200, 680, 1180, 1620],                   // altura dos 4 níveis de tubo redondo, do chão
    raioTravessa: 16,
    caixa: [380, 310, 310],                              // 5L × 4, comprimento × largura × altura
    porCamada: [3, 3], camadas: 5,                       // 3 × 3 por camada, 5 camadas = 45 caixas
  };
  const K = { montante: 0, ponteira: 1, travessa: 2, metal: 3, madeira: 4, caixa: 5, bloco: 6, sombra: 7 };

  // ── Recursos compartilhados: texturas de canvas, materiais e geometrias (criados uma vez) ──
  let R = null;
  function recursos() {
    if (R) return R;
    // Textura das caixas (uma só, atlas 256 × 512): em cima a lateral (papelão + etiqueta CAMDA 5L×4),
    // embaixo o tampo (papelão + fita sobre o vinco das abas). Branco puro = "cor do rack": o shader tinge só o
    // que é branco (fita e etiqueta) com a cor da instância; o papelão e o texto não mudam.
    const S = 256, cv = document.createElement("canvas");
    cv.width = S; cv.height = 2 * S;
    const g = cv.getContext("2d");
    g.fillStyle = "#c39a66"; g.fillRect(0, 0, S, 2 * S);
    for (let i = 0; i < 1600; i++) {                       // fibra do papelão
      const v = 150 + Math.random() * 50 | 0;
      g.fillStyle = `rgba(${v},${v * 0.78 | 0},${v * 0.52 | 0},.18)`;
      g.fillRect(Math.random() * S, Math.random() * 2 * S, 1 + Math.random() * 3, 1);
    }
    g.strokeStyle = "#86663f"; g.lineWidth = 6;           // aresta entre caixas vizinhas
    g.strokeRect(3, 3, S - 6, S - 6); g.strokeRect(3, S + 3, S - 6, S - 6);
    // lateral: etiqueta
    g.fillStyle = "#ffffff"; g.fillRect(S * 0.2, S * 0.3, S * 0.6, S * 0.36);
    g.fillStyle = "#2f5d46"; g.textAlign = "center"; g.textBaseline = "middle";
    g.font = "bold 40px Arial, sans-serif"; g.fillText("CAMDA", S * 0.5, S * 0.43);
    g.font = "bold 26px Arial, sans-serif"; g.fillText("5L × 4", S * 0.5, S * 0.57);
    g.fillStyle = "#4a3a26"; g.font = "bold 24px Arial, sans-serif"; g.fillText("↑↑", S * 0.5, S * 0.84);
    // tampo: vinco das abas + fita
    g.fillStyle = "rgba(110,80,45,.45)"; g.fillRect(0, S * 1.5 - 1, S, 2);
    g.fillStyle = "#ffffff"; g.fillRect(0, S * 1.41, S, S * 0.18);
    g.fillStyle = "rgba(0,0,0,.10)"; g.fillRect(0, S * 1.41, S, 2); g.fillRect(0, S * 1.59 - 2, S, 2);
    const caixaTex = new THREE.CanvasTexture(cv);
    caixaTex.wrapS = caixaTex.wrapT = THREE.RepeatWrapping;
    caixaTex.anisotropy = 4;

    // Furos do montante: oblongos escuros em fileira, um a cada ~50 mm
    const fv = document.createElement("canvas");
    fv.width = 16; fv.height = 32;
    const f = fv.getContext("2d");
    f.fillStyle = "#c9cdd2"; f.fillRect(0, 0, 16, 32);
    f.fillStyle = "#555a61"; f.fillRect(5, 8, 6, 14);
    const furoTex = new THREE.CanvasTexture(fv);
    furoTex.wrapS = furoTex.wrapT = THREE.RepeatWrapping;
    furoTex.magFilter = THREE.NearestFilter;

    // Tinge só o "branco" da textura (fita e etiqueta) com a cor da instância.
    const comFita = (m) => {
      m.onBeforeCompile = (sh) => {
        sh.fragmentShader = sh.fragmentShader
          .replace("#include <map_fragment>",
            "float fitaMask = 0.0;\n#ifdef USE_MAP\n bool tampo = vUv.x > 500.0;\n vec2 f = fract( vUv );\n" +
            " vec4 texelColor = texture2D( map, vec2( f.x, tampo ? f.y * 0.5 : 0.5 + f.y * 0.5 ) );\n" +
            " fitaMask = smoothstep( 0.80, 0.93, min( texelColor.r, min( texelColor.g, texelColor.b ) ) );\n" +
            " texelColor = mapTexelToLinear( texelColor );\n diffuseColor *= texelColor;\n#endif")
          .replace("#include <color_fragment>", "#ifdef USE_COLOR\n diffuseColor.rgb *= mix( vec3( 1.0 ), vColor, fitaMask );\n#endif");
      };
      m.customProgramCacheKey = () => "rack-fita";
      return m;
    };
    const metal = (cor, extra) => new THREE.MeshStandardMaterial(Object.assign({ color: cor, roughness: 0.45, metalness: 0.25 }, extra));
    R = {
      caixaTex,
      mat: {
        [K.montante]: metal(0xffffff, { map: furoTex }),
        [K.ponteira]: metal(0xbfc4ca),
        [K.travessa]: metal(0xc4c8cd),
        [K.metal]: metal(0xb3b8be),
        [K.madeira]: new THREE.MeshStandardMaterial({ color: 0xc99d66, roughness: 1, metalness: 0 }),
        [K.caixa]: comFita(new THREE.MeshStandardMaterial({ map: caixaTex, roughness: 0.9, metalness: 0 })),
        [K.bloco]: comFita(new THREE.MeshStandardMaterial({ map: caixaTex, roughness: 0.9, metalness: 0 })),
        // Sombra: uma caixa por rack que só existe no mapa de sombra (não pinta cor nem profundidade na tela).
        // As peças de verdade não projetam sombra: o mapa de sombra custa 12 triângulos por rack, perto ou longe.
        [K.sombra]: new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false }),
      },
      geo: {
        cubo: new THREE.BoxGeometry(1, 1, 1),
        travessa: new THREE.CylinderGeometry(1, 1, 1, 8, 1, true),          // tubo redondo, eixo Y
        ponteira: new THREE.ConeGeometry(Math.SQRT1_2, 1, 4, 1).rotateY(Math.PI / 4),   // pirâmide de base 1 × 1
      },
      cache: {},
    };
    R.geo.caixa = boxRepetido("caixa", 1, 1, 1);
    return R;
  }

  // Geometria unitária com os UVs repetidos por face: [x, y, z] = quantas vezes a textura cabe em cada eixo
  function boxRepetido(chave, rx, ry, rz) {
    const r = recursos();
    if (r.cache[chave]) return r.cache[chave];
    const g = new THREE.BoxGeometry(1, 1, 1), uv = g.attributes.uv;
    const porFace = [[rz, ry], [rz, ry], [rx, rz], [rx, rz], [rx, ry], [rx, ry]];   // ±x, ±y, ±z (ordem do BoxGeometry)
    for (let i = 0; i < uv.count; i++) {
      const face = Math.floor(i / 4), [u, v] = porFace[face];
      // tampo e fundo (±y) recebem +1000 em u: o shader das caixas usa a metade "tampo" do atlas
      uv.setXY(i, uv.getX(i) * u + (face === 2 || face === 3 ? 1000 : 0), uv.getY(i) * v);
    }
    return (r.cache[chave] = g);
  }

  // ── Peças de um rack, em coordenadas locais (origem no chão, no centro; lado comprido em X) ──
  // Cada peça: [tipo, x, y, z, sx, sy, sz, eixo] — eixo 'x'/'z' deita a travessa (cilindro em pé por padrão).
  function pecas({ L, P, H, camadas, caixas, perto }) {
    const mm = RACK_MM, sy = H / mm.altura, t = Math.min(mm.tubo / 1000, L * 0.08);
    const hPont = Math.max(mm.ponteira * sy, 0.035), hMont = H - hPont;   // sy converte mm → m
    const hPal = mm.palete * sy, Li = L - 2 * t, Pi = P - 2 * t;
    const [nx, nz] = mm.porCamada, bL = Li / nx, bP = Pi / nz;
    const bH = (hMont - hPal - 0.004) / camadas;
    const out = [];
    const add = (...a) => out.push(a);
    const cx = L / 2 - t / 2, cz = P / 2 - t / 2;

    // montantes até o chão, nos 4 cantos, por fora do palete
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      add(perto ? K.montante : K.metal, sx * cx, hMont / 2, sz * cz, t, hMont, t);
      if (perto) add(K.ponteira, sx * cx, hMont + hPont / 2, sz * cz, t * 0.75, hPont, t * 0.75);
    }
    // travessas nas 4 laterais (perto: tubo redondo + chapa nos cantos; longe: régua fina na moldura)
    const rt = mm.raioTravessa / 1000;
    const niveis = perto ? mm.travessas : [mm.travessas[0], mm.travessas[mm.travessas.length - 1]];
    for (const yMm of niveis) {
      const y = yMm * sy;
      for (const s of [-1, 1]) {
        if (perto) {
          add(K.travessa, 0, y, s * cz, rt, L - t, rt, "x");
          add(K.travessa, s * cx, y, 0, rt, P - t, rt, "z");
          for (const q of [-1, 1]) add(K.metal, q * cx, y, s * cz, t + 0.016, 0.075, t + 0.016);   // chapa de fixação (colar no canto)
        } else {
          add(K.metal, 0, y, s * cz, L - t, rt * 2, rt * 2);
          add(K.metal, s * cx, y, 0, rt * 2, rt * 2, P - t);
        }
      }
    }
    // palete PBR: tábuas de baixo, blocos, longarinas e tábuas de cima (longe: uma laje só)
    if (perto) {
      const e = hPal * 0.15, hb = hPal - 3 * e;
      const xs = [-Li / 2 + 0.05, 0, Li / 2 - 0.05], zs = [-Pi / 2 + 0.05, 0, Pi / 2 - 0.05];
      for (const z of zs) add(K.madeira, 0, e / 2, z, Li, e, 0.1);                        // tábuas de baixo
      for (const x of xs) for (const z of zs) add(K.madeira, x, e + hb / 2, z, 0.1, hb, 0.1);   // blocos
      for (const x of xs) add(K.madeira, x, e + hb + e / 2, 0, 0.1, e, Pi);              // longarinas
      for (let i = 0; i < 5; i++) add(K.madeira, 0, hPal - e / 2, -Pi / 2 + 0.05 + i * (Pi - 0.1) / 4, Li, e, 0.1);   // tábuas de cima
    } else {
      add(K.madeira, 0, hPal / 2, 0, Li, hPal, Pi);
    }
    add(K.sombra, 0, hMont / 2, 0, Li - 0.03, hMont - 0.03, Pi - 0.03);   // por dentro da carga: na tela o teste de profundidade descarta
    // carga: caixas 3 × 3 por camada (perto) ou um bloco com a textura repetida (longe)
    if (caixas) {
      if (perto) {
        for (let c = 0; c < camadas; c++) for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++)
          if (c === camadas - 1 || i % (nx - 1) === 0 || j % (nz - 1) === 0) add(K.caixa, -Li / 2 + bL * (i + 0.5), hPal + bH * (c + 0.5), -Pi / 2 + bP * (j + 0.5), bL - 0.006, bH - 0.004, bP - 0.006);
      } else {
        add(K.bloco, 0, hPal + (bH * camadas) / 2, 0, Li - 0.006, bH * camadas - 0.004, Pi - 0.006);
      }
    }
    return out;
  }

  // ── Lote: muitos racks em 8 InstancedMesh ───────────────────────────────────
  const _m = new THREE.Matrix4(), _base = new THREE.Matrix4(), _p = new THREE.Vector3(), _s = new THREE.Vector3();
  const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _c = new THREE.Color();
  const DEITA = { x: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, Math.PI / 2)),
                  z: new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, 0)) };
  const SEM_GIRO = new THREE.Quaternion();

  class RackLote {
    // capacidade: nº máximo de racks; L × P × H: vaga de cada rack (m); camadas: camadas de caixas
    constructor({ capacidade, L = 1.2, P = 1.0, H = RACK_MM.altura / 1000, camadas = RACK_MM.camadas, sombras = true }) {
      const r = recursos();
      Object.assign(this, { L, P, H, camadas });
      this.grupo = new THREE.Group();
      this.grupo.name = "RackLote";
      const nCx = RACK_MM.porCamada[0] * RACK_MM.porCamada[1] * camadas;
      const cap = { [K.montante]: 4, [K.ponteira]: 4, [K.travessa]: 32, [K.metal]: 36, [K.madeira]: 20, [K.caixa]: nCx, [K.bloco]: 1, [K.sombra]: 1 };
      const sy = H / RACK_MM.altura, hMont = H - Math.max(RACK_MM.ponteira * sy, 0.035);
      const geo = {
        [K.montante]: boxRepetido("mont" + Math.round(hMont * 100), 1, Math.max(1, Math.round(hMont / 0.05)), 1),
        [K.ponteira]: r.geo.ponteira, [K.travessa]: r.geo.travessa, [K.metal]: r.geo.cubo, [K.madeira]: r.geo.cubo,
        [K.caixa]: r.geo.caixa, [K.sombra]: r.geo.cubo, [K.bloco]: boxRepetido("bloco" + camadas, RACK_MM.porCamada[0], camadas, RACK_MM.porCamada[1]),
      };
      this.malhas = Object.values(K).map((k) => {
        const im = new THREE.InstancedMesh(geo[k], r.mat[k], cap[k] * capacidade);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        im.frustumCulled = false;                 // o bounding sphere da geometria não conhece as instâncias
        im.castShadow = sombras && k === K.sombra;
        im.receiveShadow = sombras && k !== K.sombra;
        im.count = 0;
        im.raycast = () => {};
        if (k === K.sombra) im.renderOrder = 1;   // por último, atrás do que já foi pintado                    // o toque é das caixas invisíveis de cada posição
        if (k === K.caixa || k === K.bloco)       // cor da fita/etiqueta por instância (tamanho da capacidade, não do count)
          im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(cap[k] * capacidade * 3), 3).setUsage(THREE.DynamicDrawUsage);
        this.grupo.add(im);
        return im;
      });
      this.limpar();
    }
    limpar() { this.n = this.malhas.map(() => 0); }
    // x, y, z: centro da base do rack; giro: rotação em Y (π/2 = lado comprido em Z); cor da fita/etiqueta
    adicionar(x, y, z, giro, { cor = 0xf4f2ed, caixas = true, perto = true } = {}) {
      _base.makeRotationY(giro).setPosition(x, y, z);
      _c.set(cor);
      for (const [k, px, py, pz, sx, sy, sz, eixo] of pecas({ L: this.L, P: this.P, H: this.H, camadas: this.camadas, caixas, perto })) {
        const im = this.malhas[k], i = this.n[k]++;
        _m.compose(_p.set(px, py, pz), eixo ? DEITA[eixo] : SEM_GIRO, _s.set(sx, sy, sz)).premultiply(_base);
        im.setMatrixAt(i, _m);
        if (im.instanceColor) im.setColorAt(i, _c);
      }
    }
    fechar() {
      this.malhas.forEach((im, k) => {
        im.count = this.n[k];
        im.visible = im.count > 0;
        im.instanceMatrix.needsUpdate = true;
        if (im.instanceColor) im.instanceColor.needsUpdate = true;
      });
    }
    descartar() { this.malhas.forEach((im) => im.dispose && im.dispose()); }
  }

  // Um rack avulso (componente reutilizável): cor da fita/etiqueta, nº de camadas, cheio ou vazio.
  function criarRack({ cor = 0xf4f2ed, camadas = RACK_MM.camadas, caixas = true, perto = true,
                       L = RACK_MM.largura / 1000, P = RACK_MM.profundidade / 1000, H = RACK_MM.altura / 1000 } = {}) {
    const lote = new RackLote({ capacidade: 1, L, P, H, camadas });
    lote.adicionar(0, 0, 0, 0, { cor, caixas, perto });
    lote.fechar();
    lote.grupo.userData.lote = lote;
    return lote.grupo;
  }

  return { RACK_MM, RackLote, criarRack, recursos };
})();
