# Galpão e loja CAMDA — mapas 3D (Streamlit)

Cópia web, **somente leitura**, dos mapas 3D do galpão e da loja do app Flutter
[LeoLira1/Gondolas](https://github.com/LeoLira1/Gondolas). Planta, numeração
(129 posições, 12 ruas, Parte 1 = 1–85, Parte 2 = 86–129 em serpentina) e regras
de saldo são portadas de `lib/galpao_config.dart`, `lib/galpao_saldo.dart` e
`lib/codigos_vinculados.dart`. Se a planta mudar lá, atualize `galpao.py`.

- **Galpão:** 129 posições, pilhas de racks, cor por saldo (vermelho/azul), busca por número e produto.
- **Loja (gôndolas e estantes):** planta de 10 × 14 m com as 12 gôndolas, estantes de parede, EDR-300,
  expositores MagnoJet/Nellore/Monitor, Estante Parede, balcão e os bonecos que caminham pelos corredores.
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
- O Python lê o Turso e injeta só um JSON de dados na cena Three.js; o token
  nunca vai para o navegador.
- Quantidades em **unidades**, sem conversão.
- Cache de leitura de 60 s (`st.cache_data`) + botão **Atualizar**.
- Sem secrets ou sem conseguir ler o banco, o app mostra **dados de exemplo** e avisa.

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
| `barracao.py` | Medidas e endereços do barracão (porte do Gondolas) |
| `cena_barracao.html` | Cena Three.js do barracão |
| `cena.html` | Cena Three.js do galpão |
| `cena_loja.html` | Cena Three.js da loja |
