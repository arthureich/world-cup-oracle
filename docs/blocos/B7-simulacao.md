B7 — Simulação
Objetivo

O B7 transforma λ, TSI, Ataque e Defesa em probabilidades reais de Copa.

λ por confronto
→ placar
→ jogo
→ grupo
→ mata-mata
→ torneio
→ Monte Carlo
Unidade do λ
λ_A, λ_B =
gols esperados nos 90 minutos

Prorrogação e pênaltis são tratados separadamente.

Modelo de placar
gols_A ~ Poisson(λ_A)
gols_B ~ Poisson(λ_B)

Probabilidades:

P(vitória A) =
Σ P(i, j), para i > j
P(empate) =
Σ P(i, j), para i = j
P(vitória B) =
Σ P(i, j), para i < j

Placar mais provável:

argmax P(i, j)
Pontos esperados
pts_esp_A =
3 · P(vitória A)
+ 1 · P(empate)
pts_esp_B =
3 · P(vitória B)
+ 1 · P(empate)
Correção de empates
MVP: Poisson puro
Refino: Dixon-Coles se o B9 mostrar problema em empates/placares baixos
Formato Copa 2026
12 grupos de 4
3 pontos por vitória
1 por empate
0 por derrota
classificam top 2 de cada grupo
+ 8 melhores terceiros
→ Round of 32
Critérios de desempate no grupo
1. pontos
2. confronto direto: pontos entre empatados
3. confronto direto: saldo entre empatados
4. confronto direto: gols marcados entre empatados
5. saldo de gols geral
6. gols marcados geral
7. fair play / team conduct
8. ranking FIFA

Na simulação pré-Copa:

não modela fair play
usa ranking FIFA como desempate residual

Durante a Copa:

se cartões reais existirem, usar fair play real antes do ranking FIFA
Melhores terceiros
1. pontos
2. saldo de gols geral
3. gols marcados geral
4. fair play
5. ranking FIFA
Chaveamento

O Round of 32 usa o Anexo C oficial:

495 combinações possíveis de melhores terceiros
carregar como dado
não deduzir em runtime
Mata-mata

90 minutos:

Poisson com λ normal

Se empate:

λ_prorrogação_A = λ_A / 3
λ_prorrogação_B = λ_B / 3
gols_prorrogação_A ~ Poisson(λ_A / 3)
gols_prorrogação_B ~ Poisson(λ_B / 3)

Se continuar empatado:

P(A vence nos pênaltis) =
clamp(
  0.5 + c_pen · (TSI_A − TSI_B),
  0.40,
  0.60
)

Com:

c_pen = 0.010
Número de simulações
dashboard rápido: 50.000
resultado estável: 200.000+
Atualizações
pré-Copa:
simula torneio inteiro

após grupos:
usa TSI/perfil atualizados e chave real

após cada jogo do mata-mata:
atualiza e re-simula o restante
