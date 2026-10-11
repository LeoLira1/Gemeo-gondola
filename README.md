# Galpão CAMDA — mapa 3D (Streamlit)

Cópia web, **somente leitura**, do mapa 3D do galpão do app Flutter
[LeoLira1/Gondolas](https://github.com/LeoLira1/Gondolas). Planta, numeração
(129 posições, 12 ruas, Parte 1 = 1–85, Parte 2 = 86–129 em serpentina) e regras
de saldo são portadas de `lib/galpao_config.dart`, `lib/galpao_saldo.dart` e
`lib/codigos_vinculados.dart`. Se a planta mudar lá, atualize `galpao.py`.

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
| `galpao.py` | Planta e regras de saldo/códigos vinculados (porte do Gondolas) |
| `cena.html` | Cena Three.js (clay, OrbitControls, buscas, tooltip) |
