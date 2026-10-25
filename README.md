# Galpão e loja CAMDA — mapas 3D (Streamlit)

Cópia web, **somente leitura**, dos mapas 3D do galpão e da loja do app Flutter
[LeoLira1/Gondolas](https://github.com/LeoLira1/Gondolas). Planta, numeração
(129 posições, 12 ruas, Parte 1 = 1–85, Parte 2 = 86–129 em serpentina) e regras
de saldo são portadas de `lib/galpao_config.dart`, `lib/galpao_saldo.dart` e
`lib/codigos_vinculados.dart`. Se a planta mudar lá, atualize `galpao.py`.

- **Galpão:** 129 posições, pilhas de racks, cor por saldo (vermelho/azul), busca por número e produto.
- **Rack misto:** o Gondolas deixa até 5 produtos no mesmo palete (o primeiro em `galpao_racks`, os outros em
  `galpao_rack_itens`). Aqui o rack misto ganha duas faixas escuras, o cartão e a dica listam todos os produtos, e a
  busca e a cor de saldo valem para qualquer um deles. Banco sem a tabela nova: o galpão segue só com os racks.
- **Loja (gôndolas e estantes):** planta de 10 × 14 m com as 12 gôndolas, estantes de parede, EDR-300,
  expositores MagnoJet/Nellore/Monitor, Estante Parede, balcão e os bonecos que caminham pelos corredores.
  No corredor central, entre a G7 e a G6, a **ilha de paletes**: 12 paletes com tapume verde (2 × 6, numerados de
  1 a 12 do caixa para a entrada), 5 produtos por palete. No banco é a estante 22 (`nivel` = espaço, `coluna` =
  produto); o cartão mostra `Espaço 3 · produto 2`. Digite `ilha` no campo Nº para ir até ela.
  Na parede da direita, entre a E1 e a cozinha, o **mostruário**: um palete de madeira com ~20 tipos de ferragem e
  ferramenta (estante 23, `nivel` = posição 0–19); o cartão mostra `Posição 7`. Digite `mostruário` (ou `E23`) no campo Nº.
  Encostado no balcão, no vão entre a G9 e a G8, o **Expositor de Madeira**: escada de 3 degraus com 6 produtos em
  cada (estante 24, `nivel` = degrau, 0 = o de baixo); o cartão mostra `Degrau de cima`. O cliente contorna ele pelo
  vão entre as gôndolas.
  Passe o mouse numa estrutura para ver os produtos e quantidades; clique para o cartão completo.
  Busca por estrutura (`G7`, `E5`) e por produto (acende em verde as estruturas que o têm).
- **Barracão:** a estrutura de 35 × 10 m (paredes de 6 m, porta, portão e porta na parede da frente) com os paletes
  e bags de `barracao_enderecos` (BAR-01 … BAR-100). Chips por fileira, busca por `BAR7` e por produto, e botão
  para alternar paredes reais / em corte. Sem linhas na tabela, mostra o layout padrão do Gondolas, todo livre.
- **Busca global:** o campo de produto de qualquer mapa procura no galpão, na loja e no barracão. O resumo mostra
  quantos locais há em cada mapa (`Galpão 3 · Loja 2 → · Barracão 1 →`), as setas abrem o outro mapa já com a busca, e a
  busca acompanha você ao trocar de aba. Os três mapas são lidos juntos (uma consulta ao Turso, cache de 60 s).
- **Escada para o mesanino (referência):** no Galpão Parte 1, paralela à Rua 1, com a base junto ao nº 14, subindo no
  sentido decrescente até o nº 11 e terminando na altura do 3º nível. Digite `escada` no campo Nº para ir até ela.
  Posição e altura vêm das posições da planta; largura (0,9 m) e folga estão em `galpao.py`.
- **Chuveiro lava-olhos (referência):** equipamento de emergência verde na Parte 1, alinhado à Rua 2 e além do nº 25, com
  altura de até 2 níveis (2,38 m). Digite `chuveiro` no campo Nº para ir até ele. A distância ao nº 25 é estimativa
  (`galpao.py`).
- **Mesa de expedição (referência):** no Galpão Parte 2, na ponta da Rua 12, além do nº 119. Mesa reta de 1,50 × 0,70 m
  (0,75 m de altura), com as duas laterais em painel cheio (sem pé de ferro) e painel de fundo, e gaveteiro embaixo do
  tampo (2 gavetas + 1 de pasta) do lado do 119. A frente dá para o corredor da Rua 11. Digite `mesa` no campo Nº para ir até ela. Medidas e
  recuo (0,60 m) estão em `galpao.py`.
- **Empilhadeira (referência, modelo 3D):** empilhadeira patolada laranja estacionada logo depois da ponta livre da
  mesa de expedição (folga de 0,50 m), alinhada à face do rack, com o timão virado para a mesa. É o modelo
  `vehicle_forklift_orange_a01` da NVIDIA SimReady convertido para `.glb` (`static/modelos/`, CC BY 4.0, ver
  `CREDITOS.md`), servido pelo `enableStaticServing` do Streamlit em `app/static/`. Digite `empilhadeira` no campo Nº
  para ir até ela. Posição e folga estão em `galpao.py`; para trocar o modelo, `EMPILHADEIRA_MODELO` e as medidas ao lado.
- **Capacidade em %:** quatro indicadores, independentes e cada um em relação às SUAS vagas, em todas as abas:
  Galpão 1 (racks ÷ 85 posições × 4 níveis), Galpão 2 (racks ÷ 44 × 4), Barracão (paletes com bag ÷ 100) e Loja
  (faixas de endereço com produto ÷ 324: gôndola = 3 andares × 6 faces, estante = um por nível, ilha = um por espaço, mostruário = um por posição). O resumo do canto do
  galpão mostra a da parte aberta.
- O Python lê o Turso e injeta só um JSON de dados na cena Three.js; o token
  nunca vai para o navegador.
- Quantidades em **unidades**, sem conversão.
- Cache de leitura de 60 s (`st.cache_data`) + botão **Atualizar**.
- Sem secrets ou sem conseguir ler o banco, o app mostra **dados de exemplo** e avisa.

## Produtos estocados (material de cooperado) — "EST:" fica fora do saldo

"Estocados" é material de cooperado que a CAMDA guarda no galpão e no barracão. Já foi faturado e saiu do sistema,
então **não entra na conta de estoque da loja** (saldo, baixa pela contagem, Modo Conferência). A lista vem de
`materiais_terceiros` (`saldo > 0`), a mesma do app Estocados.

- **Regra:** o palete de estocado tem `produto_codigo` começando por `EST:` e `produto_nome` = `PRODUTO · COOPERADO`
  (essa é a chave que liga o palete ao item; o código sozinho não serve). Paletes `EST:` **não vão para
  `estoque_localizado`** nem entram nos grupos de códigos, no saldo ou na divergência vermelho/azul deste app
  (`dados.montar`). Sem coluna nova no banco. A regra pura está em `estocados.py` (`deve_espelhar`).
- **Botão "Produtos estocados"** no galpão e no barracão: busca por cooperado, produto ou código (sem acento, vários
  termos), lista agrupada por cooperado com saldo e o endereço (`📍 Galpão 40 · N4`, `BAR-07` ou `sem endereço`).
- **Campo Produto:** também procura nos estocados (cooperado, produto ou código), inclusive itens sem endereço, e mostra
  `Estocados N itens (M sem endereço) →`; o link abre a lista já filtrada.
- **Agrupamento:** linhas do mesmo produto do mesmo cooperado (lotes, notas) viram um item só, com o saldo somado
  (`3 lançamentos`).
- **Mapa:** paletes de estocado em violeta (`#8B5CF6`).
- **Somente leitura:** lançar, ajustar e "Retirar do endereço" continuam no app Flutter Gôndolas; este app não escreve
  no banco. Quem um dia escrever aqui deve checar `deve_espelhar(codigo)` antes de gravar em `estoque_localizado`.
- Se `materiais_terceiros` não puder ser lida, a lista fica vazia e o app avisa; o resto segue.

## Rodar local

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # preencha TURSO_URL e TURSO_TOKEN
streamlit run app.py
```

Testes da lógica (opcional): `pip install pytest && pytest tests`.

## Subir no Streamlit Cloud

1. Em share.streamlit.io, crie o app apontando para este repositório, arquivo `app.py`.
2. Em **App settings → Secrets**, cole o conteúdo do `secrets.toml.example` com os valores reais.
3. O `secrets.toml` real está no `.gitignore`: nunca o versione.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `app.py` | Página Streamlit, cache, injeção do JSON na cena |
| `dados.py` | Cliente Turso (HTTP, só leitura), montagem do JSON, dados de exemplo |
| `galpao.py` | Planta e regras de saldo/códigos vinculados do galpão (porte do Gondolas) |
| `loja.py` | Planta da loja e produtos por estrutura (porte do Gondolas) |
| `ui.css`, `ui.js` | Visual e controles compartilhados pelas cenas (legenda recolhível, botão de rótulos) |
| `.streamlit/config.toml` | Tema (cores) e barra de ferramentas do Streamlit |
| `estocados.py` | Produtos estocados: busca, nome do palete, endereços, resumo de ocupação e a regra `EST:` |
| `barracao.py` | Medidas e endereços do barracão (porte do Gondolas) |
| `cena_barracao.html` | Cena Three.js do barracão |
| `cena.html` | Cena Three.js do galpão |
| `cena_loja.html` | Cena Three.js da loja |
