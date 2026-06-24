B1 — TSI — Team Strength Index
Objetivo

O TSI mede a força geral de cada seleção em uma escala de 0.000 a 20.000.

TSI ∈ [0.000, 20.000]

Interpretação:

7.000–8.000   ≈ seleções mais fracas da Copa
14.000–16.000 ≈ seleções mais fortes da Copa
16.000+       ≈ seleção histórica/absurda
20.000        ≈ teto praticamente impossível
Arquitetura

O Ranking FIFA não entra diretamente no TSI. Ele serve apenas para inicializar o Elo.

Fluxo:

Pontos FIFA
→ Elo inicial
→ Elo próprio do ciclo da Copa 2026
→ Elo ajustado por recência
→ TSI_base
→ ajuste_elenco
→ TSI_modelo
→ ajuste_odds
→ TSI_pré

Fórmulas:

TSI_base = mapear_0_20(Elo ajustado)
TSI_modelo = TSI_base + ajuste_elenco
TSI_pré = TSI_modelo + ajuste_odds
Atualização pós-grupos

O B3 gera o ajuste_desempenho.

Performance Grupo = TSI_pré + ajuste_desempenho
TSI_pós =
70% TSI_pré
+ 30% Performance Grupo

Equivalente:

TSI_pós = TSI_pré + 0.30 · ajuste_desempenho

Limite:

TSI_pós − TSI_pré ∈ [−2.000, +2.000]
