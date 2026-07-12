# Pipeline Completo

Projeto: **World Cup Oracle**

Este documento descreve a ordem de execução do sistema.

---

## Visão geral

```text
dados brutos
→ normalização
→ ratings
→ TSI
→ ataque/defesa
→ simulação
→ validação
→ dashboard/relatórios
```

---

## 1. Ingestão de dados

Entradas:

```text
pontos FIFA iniciais
partidas do ciclo Copa 2026
grupos da Copa 2026
tabela de jogos
sedes
chaveamento
Anexo C dos melhores terceiros
elencos convocados
odds de longo prazo
```

Saídas:

```text
data/raw/
data/interim/
data/processed/
```

---

## 2. Normalização

Objetivos:

```text
padronizar nomes de seleções
padronizar competições
resolver IDs
validar placares
separar pênaltis do placar oficial
marcar mando/campo neutro
classificar tipo/importância da partida
```

Regras importantes:

```text
goals_a/goals_b excluem shootout
penalty_winner guarda vencedor nos pênaltis
xG da Copa deve vir de fonte única
```

---

## 3. Elo próprio

Entrada:

```text
pontos FIFA
jogos do ciclo Copa 2026
tipo de partida
mando
placar
pênaltis
```

Processo:

```text
calcular Elo inicial
ordenar jogos por data
calcular resultado esperado
calcular resultado real
aplicar peso de importância
aplicar margem de gols
atualizar Elo jogo a jogo
calcular ajuste final por recência
```

Saída:

```text
Elo_inicial
Elo_base_final
ajuste_recência
Elo_ajustado
ranking Elo
```

---

## 4. TSI_base

Entrada:

```text
Elo_ajustado
```

Processo:

```text
mapear Elo_ajustado para escala 0.000–20.000
```

Saída:

```text
TSI_base
```

---

## 5. Ajuste de elenco

Entrada:

```text
convocados
valor de mercado
idade
minutagem recente
nível do clube/liga
posição/setor
```

Processo:

```text
corrigir valor de mercado por idade
aplicar curva de habilidade
aplicar corte de potencial para jovens
transformar valor com log(1 + valor)
agregar por setor
penalizar desbalanceamento
calcular TSI_elenco_implícito
aplicar shrinkage e cap
```

Saída:

```text
ajuste_elenco
TSI_modelo = TSI_base + ajuste_elenco
```

---

## 6. Ajuste de odds

Entrada:

```text
odds de passar de fase
odds de campeão
TSI_modelo
```

Processo:

```text
remover margem das odds
calcular força_base por logit(prob_passar)
calcular força_topo por log(prob_campeão)
padronizar força_mercado para escala do TSI_modelo
calcular ajuste_odds com cap
```

Saída:

```text
ajuste_odds
TSI_pré = TSI_modelo + ajuste_odds
```

---

## 7. Perfil, Ataque e Defesa

Entrada:

```text
TSI_pré
gols feitos/sofridos no ciclo
```

Processo:

```text
calcular Perfil_pré
Ataque = TSI + Perfil
Defesa = TSI − Perfil
```

Saída:

```text
Perfil_pré
Ataque_pré
Defesa_pré
```

---

## 8. Simulação pré-Copa

Entrada:

```text
TSI_pré
Ataque_pré
Defesa_pré
grupos
jogos
sedes
chaveamento
Anexo C
```

Processo:

```text
calcular λ por confronto
simular jogos de grupo
ordenar grupos
selecionar melhores terceiros
montar Round of 32
simular mata-mata
repetir Monte Carlo
```

Saída:

```text
probabilidade de passar de grupo
probabilidade de chegar às oitavas
probabilidade de chegar às quartas
probabilidade de semifinal
probabilidade de final
probabilidade de título
probabilidades por jogo
placar mais provável
gols esperados
```

---

## 9. Fase de grupos

Durante os grupos:

```text
esperado usa TSI/Perfil pré-Copa
não atualiza TSI no meio dos grupos
```

Após os grupos:

```text
calcular desempenho por jogo
calcular Performance Grupo
atualizar TSI
atualizar Perfil
simular mata-mata real
```

---

## 10. Pós-grupos

```text
TSI_pós =
TSI_pré + 0.30 · ajuste_desempenho
```

Com limite:

```text
TSI_pós − TSI_pré ∈ [−2.000, +2.000]
```

Perfil:

```text
calcular O
calcular D
calcular Perfil_grupos
blend com Perfil_pré
```

---

## 11. Mata-mata

Após cada jogo:

```text
atualizar dados reais
eliminar perdedor
fixar chave real restante
re-simular torneio restante
```

Times eliminados:

```text
probabilidade = 0 em todas as fases futuras
```

Comando operacional atual:

```bash
python -m world_cup_oracle.pipeline.update_after_matches
```

Por padrão, o comando não chama API. Ele usa arquivos locais/cacheados, normaliza os
detalhes disponíveis, recalcula performance, TSI atual, probabilidades, projeção de
torneio e validação.

Para buscar novos detalhes FotMob/cache:

```bash
python -m world_cup_oracle.pipeline.update_after_matches --fetch-fotmob
```

### Checkpoint 2026-07-12

Estado operacional apos as quartas:

```text
matches.csv: 100 jogos completos
worldcup_match_team_stats.csv: 200 linhas por selecao/jogo
worldcup_match_stats.parquet: 200 linhas
knockout_match_performance.parquet: 56 linhas
```

Vencedores fixados nas quartas:

```text
France, Spain, England, Argentina
```

Resultados das quartas fixados neste checkpoint:

```text
France 2-0 Morocco
Spain 2-1 Belgium
England 2-1 Norway
Argentina 3-1 Switzerland
```

Semifinais projetadas com TSI atual:

```text
France x Spain
Argentina x England
```


`Switzerland x Colombia` terminou 0-0 no placar modelado e foi decidido nos penaltis.
A classificacao usa o vencedor dos penaltis; a performance do jogo continua baseada em
placar, xG e processo sem adicionar gols da disputa.

Apos cada rodada de mata-mata concluida:

```text
1. gravar resultado bruto em data/raw/world-cup-detail/matches.csv
2. atualizar worldcup_match_ids.json e worldcup_match_team_stats.csv pelo cache FotMob
3. normalizar worldcup_match_stats.parquet
4. calcular knockout_match_performance.parquet
5. atualizar team_current_strength.parquet
6. fixar vencedores reais no bracket
7. simular apenas o restante do torneio
```

---

## 12. Validação

Entrada:

```text
previsões do modelo
resultados reais
odds jogo a jogo
placares
gols
```

Processo:

```text
calcular Brier Score
calcular Log Loss
calcular curvas de calibração
validar distribuição de gols
comparar contra odds
gerar alertas de viés
```

Saída:

```text
relatório de calibração
métricas
parâmetros recomendados
diagnósticos
```

Comando:

```bash
python -m world_cup_oracle.pipeline.validation_report
```

Artefatos:

```text
data/processed/validation_match_predictions.parquet
data/processed/validation_summary.parquet
data/processed/validation_calibration_bins.parquet
data/processed/validation_odds_comparison.parquet
docs/reports/validation-YYYY-MM-DD.md
```

---

## Ordem de execução sugerida

```text
1. ingest_data
2. normalize_data
3. build_elo
4. build_tsi_base
5. apply_squad_adjustment
6. apply_market_adjustment
7. build_attack_defense
8. simulate_tournament
9. export_outputs
10. validate_model
11. build_dashboard
```

---

## Outputs principais

```text
ratings_elo.parquet
tsi_pre_cup.parquet
attack_defense_pre_cup.parquet
match_probabilities.parquet
simulation_phase_probabilities.parquet
group_stage_performance.parquet
tsi_post_groups.parquet
validation_report.md
dashboard_data.parquet
team_stage_probabilities.parquet
knockout_match_probabilities.parquet
next_matches.parquet
validation_summary.parquet
```


