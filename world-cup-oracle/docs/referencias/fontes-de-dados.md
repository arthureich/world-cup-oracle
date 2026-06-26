# Fontes de Dados

Projeto: **Tactical Oracle**

Este documento registra as fontes necessárias, regras de uso e riscos de cobertura.

---

## Princípios

```text
usar o mínimo de fontes possível
não misturar metodologias de xG
salvar respostas brutas de API
normalizar IDs e nomes de seleções
versionar datasets processados
```

---

## Dados históricos do ciclo Copa 2026

Escopo:

```text
após Copa 2022 até antes da Copa 2026
```

Prioridade:

```text
Eliminatórias da Copa 2026
Copas continentais
Nations League / competições oficiais similares
playoffs
amistosos, se disponíveis
```

Campos necessários:

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

Para o Elo, não é necessário xG.  
O histórico precisa ser confiável em placar, competição, mando e pênaltis.

### Estratégia de coleta inicial

Prioridade prática:

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

Para `matches_cycle.parquet`, a primeira trilha é usar um CSV local de resultados
internacionais, como a base Kaggle/martj42, e API apenas para validação ou gaps.

Fluxo:

```text
baixar results.csv/shootouts.csv
→ filtrar 2022-12-19 <= date < 2026-06-11
→ normalizar nomes
→ separar pênaltis do placar
→ gerar matches_cycle.parquet
→ usar API-Football/football-data.org apenas para completar lacunas
```

Regra operacional:

```text
não buscar primeiro por seleção
buscar por competição/temporada quando usar API
```

Exemplo de comando local:

```bash
tactical-oracle-data-spike \
  --kaggle-results path/to/results.csv \
  --kaggle-shootouts path/to/shootouts.csv
```

---

## Pontos FIFA

Uso:

```text
inicializar Elo próprio
```

Regra:

```text
z-score calculado sobre todas as seleções FIFA
```

Fonte ideal:

```text
ranking FIFA pós-Copa 2022
ou primeiro ranking FIFA de 2023
```

Fonte usada no spike real:

```text
FIFA ranking masculino de 2022-12-22
rankingScheduleId=id13869
janela de partidas encerrada em 2022-12-18
payload salvo em data/raw/fifa_ranking_2022-12-22.json
```

Campos:

```text
team
fifa_points
ranking_date
fifa_rank
```

Exemplo de comando local:

```bash
tactical-oracle-data-spike \
  --fifa-ranking data/raw/fifa_ranking_2022-12-22.json
```

---

## Copa 2026 — estrutura

Dados necessários:

```text
grupos
tabela de jogos
sedes
anfitriões
placares
classificação
chaveamento
regras de melhores terceiros
Anexo C do chaveamento dos terceiros
```

O Anexo C deve ser tratado como dado estático do projeto.

### Fonte oficial usada para grupos e tabela

Competição FIFA World Cup:

```text
IdCompetition=17
IdSeason=285023
```

Payloads brutos salvos:

```text
data/raw/fifa_worldcup_2026_stages.json
data/raw/fifa_worldcup_2026_matches.json
```

Endpoints:

```text
https://api.fifa.com/api/v3/stages?IdCompetition=17&IdSeason=285023&language=en
https://api.fifa.com/api/v3/calendar/matches?IdCompetition=17&IdSeason=285023&language=en&count=120
```

Normalização:

```bash
tactical-oracle-worldcup-structure
```

Saídas atuais:

```text
data/interim/worldcup_groups.parquet
48 linhas
campos: group, team, position, fifa_rank

data/interim/worldcup_schedule.parquet
72 linhas
campos: match_id, group, team_a, team_b, match_number, host_team, neutral_site
```

Observação sobre o Anexo C:

```text
A API da FIFA expõe os placeholders do mata-mata, incluindo conjuntos possíveis de terceiros,
mas isso não é suficiente para reconstruir de forma única as 495 combinações oficiais.
O worldcup_annex_c.parquet completo continua pendente como dado estático/manual.
```

---

## Copa 2026 — estatísticas por jogo

Fonte usada no spike real:

```text
data/raw/world-cup-detail/matches.csv
data/raw/world-cup-detail/matches_detailed.csv
data/raw/world-cup-detail/match_team_stats.csv
data/raw/world-cup-detail/match_events.csv
data/raw/world-cup-detail/match_lineups.csv
```

Normalização:

```bash
tactical-oracle-worldcup-detail
```

Saídas atuais:

```text
data/interim/worldcup_match_stats.parquet
120 linhas
60 partidas concluídas × 2 seleções

data/interim/worldcup_match_events.parquet
303 linhas

data/interim/worldcup_lineups.parquet
2704 linhas
```

Observação:

```text
O match_id do pacote world-cup-detail representa o número oficial do jogo.
A normalização cruza esse valor com worldcup_schedule.match_number
para preservar o IdMatch oficial da FIFA em match_id.
```

Suplemento FotMob:

```text
data/raw/fotmob/worldcup_match_ids.json
data/raw/fotmob/worldcup_match_team_stats.csv
data/raw/fotmob/get_matches_by_date/*.json
data/raw/fotmob/get_match_details/*.json
```

Uso atual:

```text
FotMob via Parse.bot é a fonte preferencial para xG e métricas de processo.
world-cup-detail segue como base oficial local de calendário, elencos e estrutura.
Quando existe detalhe FotMob, ele sobrepõe placar, data, status, xG e stats do jogo.
Quando só existe cache diário com placar, a partida entra como score-only.
```

Estado do cache FotMob:

```text
60 partidas carregadas em worldcup_match_team_stats.csv
56 partidas com detalhe completo via get_match_details
4 partidas com estatísticas preenchidas manualmente a partir do FotMob:
- Japan 1-1 Sweden
- Tunisia 1-3 Netherlands
- Turkey 3-2 United States
- Paraguay 0-0 Australia
```

Observação:

```text
Turkey 3-2 United States e Paraguay 0-0 Australia ainda não têm JSON bruto
FotMob no cache. O placar foi inferido das estatísticas copiadas manualmente
usando shots_on_target − keeper_saves.
```

Essenciais:

```text
gols
gols sofridos
xG
xG sofrido
chances claras
chances claras cedidas
touches in opposition box
touches in opposition box cedidos
opposition half passes
opposition half passes cedidos
ground duels won
ground duels won %
successful dribbles
successful dribbles %
posse de bola
cartão vermelho
minuto do cartão vermelho
```

Importantes se disponíveis:

```text
momentum / attacking momentum
escalação titular
substituições relevantes
rotação/poupança
necessidade competitiva do jogo
```

Baixa relevância:

```text
escanteios
cartões amarelos
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

---

## Regra de fonte única para xG

O xG deve vir de uma única fonte principal.

Motivo:

```text
xG varia por provedor
misturar provedores quebra a calibração
```

Regra:

```text
usar FotMob como fonte principal de xG/stats da Copa quando disponível
não misturar xG de provedores diferentes na mesma partida
se faltar detalhe FotMob, a partida pode entrar como score-only
```

Outra fonte pode ser usada apenas para conferência manual.

---

## Elenco

Fonte usada no spike real:

```text
data/raw/world-cup-detail/teams.csv
data/raw/world-cup-detail/squads_and_players.csv
```

Saídas atuais:

```text
data/interim/worldcup_teams_detail.parquet
48 linhas

data/interim/squads.parquet
1248 linhas
```

Fonte de valor de mercado:

```text
Transfermarkt export filtrado por jogadores da Copa
fonte preferida: dcaribou/transfermarkt-datasets
https://github.com/dcaribou/transfermarkt-datasets
```

Motivo da escolha:

```text
dataset estruturado e atualizado semanalmente
inclui players e player_valuations
inclui histórico de valor de mercado
inclui date_of_birth para cruzamento mais seguro por jogador
inclui campos de seleção nacional para apoio, mas o roster oficial continua vindo da Copa
```

Arquivos recomendados:

```text
players.csv.gz
player_valuations.csv.gz
```

Download local:

```bash
mkdir -p data/raw/transfermarkt
curl -L -o data/raw/transfermarkt/players.csv.gz \
  https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz
curl -L -o data/raw/transfermarkt/player_valuations.csv.gz \
  https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz
```

O campo `market_value_eur` em `world-cup-detail/squads_and_players.csv` foi mantido
apenas como metadado bruto e não deve alimentar o TSI. Alguns valores estão defasados
ou incompatíveis com a realidade, então a normalização marca:

```text
market_value_source = world-cup-detail
market_value_trusted = false
```

Para habilitar o ajuste de elenco, usar um dataset Transfermarkt confiável:

```bash
tactical-oracle-transfermarkt-squads \
  --players-csv data/raw/transfermarkt/players.csv.gz \
  --valuations-csv data/raw/transfermarkt/player_valuations.csv.gz \
  --as-of 2026-06-11
```

Esse comando cruza os jogadores por nome normalizado e data de nascimento, pega a
valoração mais recente até a data de corte e regrava `squads.parquet` com:

```text
market_value_source = transfermarkt
market_value_trusted = true
market_value_date
transfermarkt_player_id
```

Regra de cobertura para ativar ajuste de elenco:

```text
trusted_player_count >= 22
trusted_coverage >= 0.80
```

Se a cobertura ficar abaixo disso, a seleção permanece com `ajuste_elenco = 0.000`
para evitar punir jogadores ausentes no cruzamento como se tivessem valor zero.

Fontes para minutagem e nível de clube:

```text
FotMob
FBref
```

Escopo:

```text
somente convocados oficiais
sem modelar ausências separadamente
roda após anúncio dos elencos
```

Campos:

```text
player_id
player_name
team
age
position
club
market_value
recent_minutes
club_level
league_level
called_up
```

No dataset atual, `recent_minutes_factor`, `club_level`, `league_level` e `status`
entram neutros como 1.000. O ajuste de elenco usa valor de mercado como âncora direta
e balanço setorial apenas quando a fonte de mercado está marcada como confiável;
refinamentos de minutagem/nível de clube ficam para uma fonte posterior.

---

## Odds

Fonte recomendada para automação:

```text
The Odds API
https://the-odds-api.com
```

Sport keys relevantes:

```text
soccer_fifa_world_cup         odds jogo a jogo
soccer_fifa_world_cup_winner  campeão / outright
```

Mercados:

```text
h2h       vitória/empate/vitória no futebol
outrights campeão/futuros
```

Observação operacional:

```text
passar de fase é desejável para B6, mas não deve bloquear o pipeline se não houver
mercado consistente via API; nesse caso, usar campeão/outrights como calibração leve
e reservar odds jogo a jogo para B9.
```

Exemplos de endpoints:

```text
GET /v4/sports/soccer_fifa_world_cup/odds/?markets=h2h&regions=eu,uk
GET /v4/sports/soccer_fifa_world_cup_winner/odds/?markets=outrights&regions=eu,uk
```

Salvar payload bruto antes de normalizar:

```text
data/raw/odds_api/{sport_key}/{market}/{snapshot_date}.json
```

### B6 — odds de longo prazo

Usadas para ajuste leve:

```text
passar de fase
campeão
```

### B9 — odds jogo a jogo

Usadas para validação:

```text
vitória A
empate
vitória B
```

Separação:

```text
B6 usa mercados de longo prazo
B9 usa mercado jogo a jogo
```

---

## API-Football

O plano gratuito com 100 requests/dia pode ser útil, mas exige cuidado.

Uso recomendado:

```text
spike de cobertura
validação de dados
preenchimento de gaps
dados da Copa, se o plano permitir
```

Não assumir como fonte única antes de testar:

```text
cobertura de seleções pequenas
amistosos
pênaltis
fase/competição
campo neutro
IDs consistentes
```

### Cache obrigatório

```text
data/raw/api_football/{endpoint}/{params_hash}/{date}.json
```

Regra:

```text
se já baixou, não chama a API de novo
```

---

## Estratégia prática

Camadas:

```text
1. base aberta histórica, se encontrada
2. API-Football para validação/gaps
3. correções manuais pontuais
4. Parquet final normalizado
```

Para a Copa 2026:

```text
poucos jogos → possível corrigir manualmente
maior cuidado com xG/stats e fonte única
```

---

## Outputs normalizados

```text
teams.parquet
matches_cycle.parquet
fifa_rankings.parquet
worldcup_groups.parquet
worldcup_schedule.parquet
worldcup_annex_c.parquet
worldcup_match_stats.parquet
worldcup_match_events.parquet
worldcup_lineups.parquet
worldcup_teams_detail.parquet
squads.parquet
odds_long_term.parquet
odds_match_by_match.parquet
```
