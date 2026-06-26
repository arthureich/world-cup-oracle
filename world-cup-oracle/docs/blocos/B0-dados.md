# B0 - Dados

## Objetivo

O B0 define quais dados o projeto precisa para calcular forca das selecoes, gerar
probabilidades por jogo, simular a Copa e validar o modelo.

O B0 nao define formulas de forca. Ele define entradas, fontes e regras de dados.

## Escopo Historico

O escopo foi simplificado para o ciclo da Copa 2026.

```text
Ciclo Copa 2026 =
apos a Copa 2022 ate antes da Copa 2026
```

Uso principal:

```text
Elo proprio
Perfil pre-Copa
base historica recente
```

Prioridade de dados:

```text
Eliminatorias da Copa 2026
Copas continentais
Nations League / competicoes oficiais similares
playoffs
amistosos, se disponiveis
```

O modelo nao tenta reconstruir toda a historia recente do futebol internacional.
Ele mede a forca das selecoes dentro do ciclo competitivo da Copa 2026.

## Partidas Historicas Do Ciclo

Campos necessarios:

```text
match_id
date
team_a
team_b
goals_a
goals_b
competition
stage
match_type
home_team
neutral_site
went_to_penalties
penalty_winner
```

Definicao de placar:

```text
goals_a / goals_b =
placar ao fim do jogo, incluindo prorrogacao,
mas excluindo disputa de penaltis
```

```text
penalty_winner =
selecao vencedora da disputa de penaltis
```

Isso evita que a margem de gols do Elo conte gols de shootout.

## Pontos FIFA Iniciais

Os pontos FIFA sao usados apenas para inicializar o Elo.

O z-score dos pontos FIFA deve ser calculado sobre todas as selecoes FIFA, nao
apenas sobre as 48 classificadas.

```text
z_score =
(pontos_fifa - media_pontos_fifa)
/
desvio_padrao_pontos_fifa
```

## Estatisticas Da Copa 2026

Para a Copa 2026, os dados sao mais completos porque alimentam o desempenho por
jogo e o Perfil de grupos.

Estatisticas essenciais:

```text
gols
gols sofridos
xG
xG sofrido
chutes
chutes sofridos
chutes no alvo
chutes no alvo sofridos
chances claras
chances claras cedidas
posse de bola
cartao vermelho
minuto do cartao vermelho
```

Importantes se disponiveis:

```text
momentum / attacking momentum
escalacao titular
substituicoes relevantes
rotacao/poupanca
necessidade competitiva do jogo
```

Baixa relevancia, mas armazenaveis:

```text
escanteios
cartoes amarelos
faltas
impedimentos
```

Fora do escopo:

```text
mapa de chutes
kickoff_time
rest_days
travel_distance
```

## Regra De Fonte Unica Para xG

xG e estatisticas avancadas da Copa devem vir de uma unica fonte.

Nao misturar provedores diferentes, porque xG muda por metodologia e isso
bagunca a calibracao.

## Dados Especificos Da Copa 2026

Necessarios:

```text
grupos
jogos
placares
classificacao dos grupos
chaveamento
regras dos melhores terceiros
anfitrioes
sede/estadio, se necessario
Anexo C do chaveamento dos terceiros
```

Frequencia de atualizacao:

```text
1. TSI inicial pre-Copa
2. Atualizacao apos fase de grupos
3. Atualizacao apos cada jogo do mata-mata
```

## Plano Pratico De Coleta

O gargalo atual do projeto e coleta, normalizacao e validacao de dados reais.

A ordem recomendada e:

```text
1. matches_cycle.parquet
2. fifa_points.parquet
3. worldcup_groups.parquet
4. worldcup_schedule.parquet
5. worldcup_annex_c.parquet
6. squads.parquet
7. odds_long_term.parquet
8. odds_match_by_match.parquet
```

## Prioridade 1: Destravar O Elo

Para `matches_cycle.parquet`, comecar com uma base aberta de resultados
internacionais e usar API apenas para completar lacunas.

Fonte inicial recomendada:

```text
Kaggle / martj42 international football results
```

Motivo:

```text
base focada em selecoes masculinas
cobre amistosos e competicoes oficiais
cobre dezenas de milhares de jogos internacionais
resolve boa parte do ciclo 2023-2025
```

Fluxo:

```text
baixar Kaggle
filtrar date >= pos-Copa 2022
filtrar date < Copa 2026
normalizar nomes
gerar matches_cycle.parquet
usar API-Football / football-data.org apenas para 2026 e gaps
```

Evitar buscar por selecao, porque isso consome muitas requests e duplica jogos.

Evitar:

```text
Brasil 2023
Brasil 2024
Brasil 2025
Franca 2023
Franca 2024
Franca 2025
```

Preferir buscar por competicao / temporada:

```text
Eliminatorias CONMEBOL 2026
Euro 2024
Copa America 2024
AFCON
Asian Cup
Gold Cup
Nations League
playoffs
amistosos, se necessario
```

API-Football e candidata para completar gaps, mas deve ser usada com cache
obrigatorio por causa do limite gratuito.

football-data.org tambem pode ajudar em competicoes especificas, mas a cobertura
de selecoes, eliminatorias e amistosos precisa ser testada.

## Prioridade 2: Pontos FIFA

Para `fifa_points.parquet`, usar o ranking oficial FIFA.

Campos necessarios:

```text
team
fifa_points
ranking_date
fifa_rank
```

Data recomendada:

```text
ranking pos-Copa 2022
ou primeiro ranking de 2023
```

Regra:

```text
os pontos FIFA inicializam o Elo proprio
os pontos FIFA nao entram diretamente no TSI
```

## Prioridade 3: Estrutura Da Copa 2026

Esses arquivos podem comecar manuais porque sao pequenos e precisam estar
corretos:

```text
worldcup_groups.parquet
worldcup_schedule.parquet
worldcup_annex_c.parquet
```

O arquivo mais critico e:

```text
worldcup_annex_c.parquet
```

Ele deve conter todas as combinacoes possiveis dos 8 melhores terceiros:

```text
C(12, 8) = 495 combinacoes
```

Regra:

```text
o Anexo C deve ser carregado como dado estatico
o Anexo C nao deve ser inferido pelo codigo
```

## Prioridade 4: Elencos

Para `squads.parquet`, comecar com CSV manual ou semi-manual.

Nao tentar automatizar Transfermarkt, FBref e FotMob antes do pipeline real rodar
de ponta a ponta.

Campos:

```text
player_id
player_name
team
age
sector
club
market_value
recent_minutes_factor
club_level
league_level
status
called_up
```

Fontes candidatas:

```text
Transfermarkt para valor de mercado
FBref / FotMob para minutagem e clube
planilha manual controlada para o MVP
```

## Prioridade 5: Odds

Separar os usos:

```text
B6 usa odds de longo prazo
B9 usa odds jogo a jogo
```

Arquivo B6:

```text
odds_long_term.parquet
```

Campos completos, quando houver mercado de classificacao e campeao:

```text
team
pass_yes
pass_no
champion
bookmaker
timestamp
```

Para o MVP, se houver apenas mercado de campeao da Copa, usar snapshot
champion-only:

```text
snapshot_date
source
bookmaker
source_team
team
market
american_odd
champion
champion_probability_raw
champion_probability_devig
```

Regra:

```text
american_odd -> odds decimal
probabilidade bruta = 1 / odds decimal
probabilidade devig = probabilidade bruta / soma das probabilidades brutas
ajuste B6 = z(log(probabilidade devig)) mapeado para a escala do TSI_modelo
cap = odds_adjustment_cap
```

Comando para normalizar o snapshot manual:

```bash
tactical-oracle-normalize-outrights
```

Entrada padrao:

```text
data/raw/manual/odds_worldcup_winner_snapshot.csv
```

Saida padrao:

```text
data/interim/odds_long_term.parquet
```

Arquivo B9:

```text
odds_match_by_match.parquet
```

Campos:

```text
match_id
team_a
team_b
odd_a
odd_draw
odd_b
bookmaker
timestamp
```

The Odds API e candidata para odds jogo a jogo e outrights/futures, dependendo da
cobertura disponivel para Copa do Mundo.

## Coleta De Odds Futuras

No plano gratuito, The Odds API deve ser usada para snapshots futuros/upcoming,
nao para historico.

Regra operacional:

```text
THE_ODDS_API_KEY deve ficar em variavel de ambiente
apiKey nao deve ser salvo em data/raw
todo payload bruto deve passar pelo cache local
```

Comando:

```bash
tactical-oracle-collect-odds --sport upcoming --regions eu
```

Saidas:

```text
data/raw/api_cache/the_odds_api/...
data/interim/odds_match_by_match.parquet
```

Uso recomendado:

```text
B9:
  coletar h2h de jogos futuros quando eles aparecerem na API
  construir historico proprio de snapshots a partir de agora

B6:
  usar outrights/futures apenas se a Copa 2026 estiver disponivel
  caso contrario, manter odds_long_term.parquet manual/semi-manual
  ou usar ajuste_odds = 0 ate haver mercado confiavel
```

## Data Spike Recomendado

Entrega 1: Elo com dado real

```text
baixar Kaggle / martj42
filtrar ciclo Copa 2026
normalizar colunas
gerar matches_cycle.parquet
pegar ranking FIFA inicial
gerar fifa_points.parquet
rodar Elo
```

Entrega 2: estrutura da Copa

```text
worldcup_groups.parquet
worldcup_schedule.parquet
worldcup_annex_c.parquet
```

Mesmo com selecoes ainda mockadas, isso destrava a simulacao.

Entrega 3: ajustes

```text
squads.parquet
odds_long_term.parquet
odds_match_by_match.parquet
```

Esses melhoram o modelo, mas nao bloqueiam o nucleo Elo / TSI / simulacao.

## Auditoria De Dados

Antes de recalcular outputs oficiais, rodar:

```bash
tactical-oracle-audit-data
```

Saidas:

```text
data/processed/data_quality_report.parquet
data/processed/squad_coverage.parquet
data/processed/odds_long_term_coverage.parquet
```

Uso:

```text
data_quality_report.parquet:
  PASS/WARN/FAIL dos inputs reais

squad_coverage.parquet:
  26 jogadores, cobertura confiavel, setores e valor agregado por selecao

odds_long_term_coverage.parquet:
  cobertura das odds de campeao, aliases e probabilidade devig por selecao
```

Data lock atual:

```text
docs/reports/data-lock-2026-06-25.md
```

## Anexo C

O Anexo C oficial deve ser extraido do PDF local:

```text
data/raw/annex-c.pdf
```

Comando:

```bash
tactical-oracle-extract-annex-c --pdf data/raw/annex-c.pdf
```

Saida:

```text
data/interim/worldcup_annex_c.parquet
```

Validacao:

```bash
tactical-oracle-validate-annex-c data/interim/worldcup_annex_c.parquet --complete
```

## Imputacao De Valores De Elenco

Quando um jogador do elenco nao tiver valor confiavel, preencher com a media dos
jogadores confiaveis da propria selecao:

```bash
tactical-oracle-impute-squads
```

Regra aplicada:

```text
market_value = media dos jogadores confiaveis do time
market_value_eur = mesma media
market_value_source = team_mean_imputed
market_value_imputed = true
market_value_trusted = true para uso no modelo
```

## Decisao Operacional

Comecar por:

```text
Kaggle international results
ranking FIFA oficial
CSV manual da estrutura da Copa
```

Depois:

```text
API-Football para gaps
The Odds API para odds
Transfermarkt / FBref / FotMob para elenco
```
