# World Cup Oracle - Visao Geral

## O que e o projeto

**World Cup Oracle** e um sistema analitico para modelar a Copa do Mundo 2026.

Ele junta dados historicos, elenco, mercado, estatisticas de jogo e simulacao para
responder perguntas praticas:

- qual selecao esta mais forte agora;
- qual e a chance de cada selecao vencer um jogo;
- quantos gols cada confronto deve produzir;
- qual caminho mais provavel no mata-mata;
- qual probabilidade de cada selecao chegar em cada fase;
- como a forca muda depois da fase de grupos e de jogos do mata-mata;
- se o modelo esta calibrado ou confiante demais.

O foco do projeto nao e "cravar" um campeao. O foco e produzir probabilidades coerentes,
auditaveis e atualizaveis conforme novos jogos entram.

---

## Como pensar no sistema

Uma forma simples de ver o projeto:

```text
dados brutos
-> tabelas normalizadas
-> rating das selecoes
-> gols esperados por confronto
-> simulacao de jogos e torneio
-> dashboard e relatorios
-> validacao do modelo
```

O dado entra em `data/raw`, vira tabelas limpas em `data/interim`, e depois gera outputs
analiticos em `data/processed`. O Streamlit le esses outputs e apresenta ranking,
probabilidades, bracket e diagnosticos.

---

## A metrica central: TSI

A metrica principal e o **TSI - Team Strength Index**.

```text
TSI = forca geral da selecao
escala = 0 a 20
```

Interpretacao aproximada:

```text
7-9    selecoes fracas ou de baixo teto no torneio
10-12  selecoes medias
13-14  selecoes competitivas
15-16  candidatas fortes
16+    selecao historicamente muito acima do campo
```

O TSI nao e simplesmente FIFA, Elo, elenco ou odds. Ele e uma composicao:

```text
pontos FIFA
-> Elo inicial
-> Elo proprio do ciclo 2026
-> TSI_base
-> ajuste de calendario
-> ajuste de elenco
-> TSI_modelo
-> ajuste de odds
-> TSI_pre
-> TSI atual / pos-grupos / pos-mata-mata
```

Em termos de dados:

- FIFA inicializa o Elo, mas nao entra diretamente no TSI final;
- Elo mede resultado historico no ciclo da Copa 2026;
- calendario corrige adversarios mais faceis ou mais duros;
- elenco captura qualidade atual dos convocados;
- odds entram como ajuste leve de mercado;
- desempenho real na Copa atualiza a forca depois dos grupos e durante o mata-mata.

---

## Dados usados

O projeto trabalha com tabelas pequenas e locais em Parquet. Isso deixa o pipeline
reprodutivel e facil de debugar.

Principais entradas:

- `matches_cycle`: jogos internacionais do ciclo da Copa 2026;
- `fifa_points`: ranking/pontos FIFA usados no Elo inicial;
- `worldcup_groups`: grupos da Copa;
- `worldcup_schedule`: calendario e chaveamento;
- `worldcup_annex_c`: combinacoes oficiais dos melhores terceiros;
- `squads`: convocados, setor, idade, clube e valor;
- `odds_long_term`: odds pre-Copa de campeao/passagem;
- `odds_match_by_match`: odds jogo a jogo para validacao;
- `worldcup_match_stats`: gols, xG e estatisticas FotMob da Copa.

Regra importante de placar:

```text
goals_a/goals_b excluem disputa de penaltis
penalty_winner guarda o vencedor dos penaltis
```

Isso evita contaminar Elo, Poisson e validacao de gols com uma disputa que nao e parte do
placar modelado.

---

## Elo proprio

O Elo proprio mede forca historica recente no ciclo 2026.

Ele usa:

- pontos FIFA como ponto de partida;
- resultado esperado;
- resultado real;
- mando;
- peso de importancia da competicao;
- margem de gols com teto;
- penaltis como quase empate;
- ajuste de recencia.

Formula base:

```text
novo_Elo =
Elo_atual
+ K * peso_importancia * multiplicador_margem * (resultado_real - resultado_esperado)
```

O resultado esperado segue a formula classica do Elo:

```text
E_A = 1 / (1 + 10 ^ ((Elo_B - Elo_A_ajustado) / 400))
```

Depois do ciclo, o Elo ajustado e transformado em `TSI_base`.

---

## Elenco

O ajuste de elenco tenta responder:

> O time que os resultados historicos descrevem ainda parece o time que vai jogar agora?

Para isso, o projeto agrega jogadores por setor:

```text
GOL, DEF, MEI, ATA
```

Cada jogador entra com valor de mercado ajustado, e o valor e comprimido:

```text
valor_agregado_jogador = log(1 + valor_efetivo)
```

Depois o sistema calcula z-score por setor contra as outras selecoes. Assim, uma selecao
nao e avaliada isoladamente: ela e comparada com o campo da Copa.

O score de elenco combina:

- media dos setores;
- penalidade para setor criticamente fraco;
- transformacao para a escala do TSI;
- cap para impedir que elenco sozinho reescreva o modelo.

---

## Odds

As odds entram em dois lugares diferentes.

No **B6**, odds de longo prazo ajustam levemente o TSI pre-Copa:

- campeao;
- passar de fase, quando disponivel.

No **B9**, odds jogo a jogo sao usadas apenas para validacao:

- comparar Log Loss do modelo contra mercado;
- comparar Brier Score;
- detectar quando o modelo esta muito longe da precificacao externa.

Isso evita circularidade: odds do proprio jogo nao sao usadas para prever esse mesmo jogo.

---

## Ataque, defesa e gols esperados

Depois do TSI, a forca e separada em dois componentes:

```text
Ataque = TSI + Perfil
Defesa = TSI - Perfil
```

O `Perfil` nao e forca. Ele representa estilo/abertura:

- perfil positivo tende a jogos mais abertos;
- perfil negativo tende a jogos mais travados.

Para transformar forca em gols esperados, o modelo usa uma curva exponencial com uma
transformacao sublinear no gap de TSI. Isso aumenta diferencas pequenas de forma util,
mas evita xG absurdo quando a diferenca de forca e muito grande.

```text
d = TSI_A - TSI_B
V(d) = sinal(d) * min(V_max, a * |d|^p)

lambda_A = base_goals * exp(k * (V(d) + profile_signal))
lambda_B = base_goals * exp(k * (-V(d) + profile_signal))
```

Parametros atuais:

```text
base_goals = 1.30
k = 0.18
a = 1.25
p = 0.60
V_max = 3.00
profile_signal = 0.25 * (Perfil_A + Perfil_B)
```

Para anfitriao:

```text
lambda_host = lambda * exp(gamma)
lambda_opp = lambda * exp(-delta)
```

com `gamma = 0.15` e `delta = 0.00`.

---

## Probabilidades de partida

Com os gols esperados, o modelo calcula a distribuicao de placares:

```text
gols_A ~ Poisson(lambda_A)
gols_B ~ Poisson(lambda_B)
```

Disso saem:

- probabilidade de vitoria A em 90 minutos;
- probabilidade de empate;
- probabilidade de vitoria B em 90 minutos;
- placar mais provavel;
- pontos esperados na fase de grupos;
- probabilidade de avancar em mata-mata, incluindo prorrogacao e penaltis.

No mata-mata:

```text
90 minutos -> Poisson normal
empate -> prorrogacao com lambda / 3
novo empate -> penaltis com vantagem limitada por TSI
```

---

## Simulacao da Copa

O simulador usa Monte Carlo para repetir a Copa muitas vezes.

Formato:

```text
12 grupos de 4
1o e 2o de cada grupo classificam
8 melhores terceiros classificam
Round of 32
mata-mata ate a final
```

O Anexo C oficial define como os melhores terceiros entram no chaveamento. Ele e carregado
como dado, nao inferido por regra improvisada.

Saidas principais:

- probabilidade de chegar em cada fase;
- probabilidade de titulo;
- confronto mais provavel por slot do mata-mata;
- vencedor mais provavel de cada duelo;
- xG e chance de avancar em cada jogo;
- tabela de proximas partidas;
- bracket projetado no dashboard.

---

## Atualizacao durante a Copa

O projeto ja tem um comando para atualizar o pipeline depois que novas partidas entram:

```bash
python -m tactical_oracle.pipeline.update_after_matches
```

Por padrao ele nao gasta API. Ele usa o que ja esta no cache/local, normaliza os dados e
recalcula:

- estatisticas de partida;
- performance por jogo;
- TSI atual;
- ataque/defesa atualizados;
- probabilidades das proximas partidas;
- projecao de grupos e mata-mata;
- relatorio de validacao.

Para buscar dados novos no FotMob/cache da API:

```bash
python -m tactical_oracle.pipeline.update_after_matches --fetch-fotmob
```

Flags manuais tambem existem para jogos de terceira rodada ou contexto especial:

- selecao ja garantida em primeiro: reduz levemente a forca no calculo daquele jogo;
- selecao poupando jogadores: reduz de forma mais forte.

Essas flags entram manualmente na tabela de calendario/partidas porque detectar isso por
dado estruturado seria complexo e fragil no MVP.

---

## Dashboard

O Streamlit apresenta o modelo como produto analitico, nao como pagina de marketing.

As telas principais mostram:

- ranking TSI atual;
- probabilidades por fase;
- proximas partidas;
- xG e chance de vitoria/empate/derrota;
- chance de avancar em mata-mata incluindo prorrogacao e penaltis;
- bracket projetado;
- selecao individual com caminho e chance por etapa;
- relatorios de validacao e auditoria.

No bracket:

- jogos confirmados aparecem separados dos projetados;
- jogos projetados mostram a probabilidade de aquele confronto acontecer;
- cada card mostra chance de avancar e gols esperados de forma compacta.

---

## Validacao

O modelo e validado em cima das partidas ja jogadas.

Metricas atuais:

- Brier Score;
- Log Loss;
- Expected Calibration Error;
- calibration bins;
- log-likelihood do placar exato;
- comparacao contra odds jogo a jogo, quando o arquivo existir.

Comando:

```bash
python -m tactical_oracle.pipeline.validation_report
```

Saidas:

```text
data/processed/validation_match_predictions.parquet
data/processed/validation_summary.parquet
data/processed/validation_calibration_bins.parquet
data/processed/validation_odds_comparison.parquet
docs/reports/validation-YYYY-MM-DD.md
```

Essa parte e importante porque o modelo deve melhorar por evidencia, nao por sensacao.
Se uma curva mais complexa nao melhora Brier, Log Loss ou calibracao de forma consistente,
ela nao deve substituir uma versao mais simples.

---

## Stack

Stack atual:

```text
Python
Polars
Parquet
NumPy / SciPy
Streamlit
pytest
Markdown
```

O MVP e local e analitico. Nao usa Spark, PostgreSQL, FastAPI ou React.

---

## Principio do projeto

O World Cup Oracle trata futebol como distribuicao de possibilidades.

Uma selecao com 70% de chance ainda perde muitas vezes. Uma selecao com 20% ainda tem um
caminho real. A qualidade do modelo esta em estimar essas chances com escala, coerencia e
calibracao.

Por isso, cada numero importante deve ter:

- dado de origem;
- formula ou metodo;
- output em Parquet;
- forma de auditoria;
- validacao posterior.
