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

Campos:

```text
team
fifa_points
ranking_date
fifa_rank
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

---

## Copa 2026 — estatísticas por jogo

Essenciais:

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
escolher uma fonte principal de xG/stats da Copa
não misturar com outra fonte no mesmo modelo
```

Outra fonte pode ser usada apenas para conferência manual.

---

## Elenco

Fonte de valor de mercado:

```text
Transfermarkt
```

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

---

## Odds

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
squads.parquet
odds_long_term.parquet
odds_match_by_match.parquet
```
