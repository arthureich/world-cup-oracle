# Parâmetros

Projeto: **World Cup Oracle**

Lista dos parâmetros principais, valores iniciais e pontos recalibráveis.

---

## Elo próprio — B2

| Parâmetro | Valor | Status |
|---|---:|---|
| `Elo_base` | 1500 | Inicial |
| `fator_z_fifa` | 120 | Recalibrável |
| `Elo_min` | 1100 | Recalibrável |
| `Elo_max` | 1900 | Recalibrável |
| `K` | 25 | Recalibrável |
| `mando_elo` | +50 | Recalibrável |
| `meia_vida_recência` | 24 meses | Recalibrável |
| `amostra_recência_ref` | 8 | Recalibrável |
| `multiplicador_recência` | 10 | Recalibrável |
| `cap_ajuste_recência` | ±80 Elo | Recalibrável |

---

## Pesos por importância — B2

| Tipo de partida | Peso |
|---|---:|
| Amistoso | 0.50 |
| Nations League / similar | 0.80 |
| Eliminatórias | 1.00 |
| Continental grupos | 1.20 |
| Continental mata-mata | 1.50 |
| Copa do Mundo grupos | 1.80 |
| Copa do Mundo mata-mata | 2.20 |

---

## Margem de gols — B2

```text
multiplicador_margem =
1 + 0.4 · (1 − exp(−(0.277·x + 0.006·x^2.97)))
```

| Parâmetro | Valor |
|---|---:|
| teto adicional | 0.4 |
| coeficiente linear | 0.277 |
| coeficiente não linear | 0.006 |
| expoente | 2.97 |
| teto aproximado | 1.400 |

---

## TSI — B1

| Parâmetro | Valor | Status |
|---|---:|---|
| escala mínima | 0.000 | Estrutural |
| escala máxima | 20.000 | Estrutural |
| centro do mapeamento real por coorte FIFA | 10.000 | Inicial |
| escala z do mapeamento real por coorte FIFA | 2.25 | Recalibrável |
| piso TSI para baseline de calendário contender | 13.000 | Recalibrável |
| ajuste calendário por 100 Elo de adversário | 0.250 | Recalibrável |
| cap ajuste calendário | ±0.350 | Recalibrável |
| peso TSI pré no pós-grupos | 70% | Recalibrável |
| peso Performance Grupo | 30% | Recalibrável |
| cap variação pós-grupos | ±2.000 | Recalibrável |

Regra atual dos outputs reais:

```text
TSI_base = clamp(10.0 + 2.25 · z(Elo_ajustado), 0.000, 20.000)
```

Isso evita que outliers de Elo recente encostem em 20.000 antes dos ajustes de elenco,
odds e validação.

Ajuste de calendário dos outputs reais:

```text
média_adversários =
média(Elo_ajustado dos adversários enfrentados no ciclo)

baseline_contender =
média(média_adversários das seleções com TSI_base >= 13.000)

ajuste_calendário =
clamp(
  0.250 · (média_adversários − baseline_contender) / 100,
  -0.350,
  +0.350
)
```

Esse ajuste é propositalmente menor que elenco e odds. Ele serve para reduzir viés de
calendário, não para substituir o Elo partida a partida.

---

## Desempenho por jogo — B3

| Parâmetro | Valor | Status |
|---|---:|---|
| `c_proc` | 4.0 | Recalibrável |
| `c_res` | 3.0 | Recalibrável |
| `actual_gd_influence` | 0.15 | Recalibrável |
| `match_delta_soft_cap` | 4.0 | Recalibrável |
| piso `peso_jogo` | 0.15 | Recalibrável |
| `ρ_vermelho` | 0.5 | Recalibrável |
| rotação pesada | ~0.40 | Recalibrável |

Composto ofensivo:

| Métrica | Peso |
|---|---:|
| xG criado | 45% |
| chances claras | 25% |
| touches in opposition box | 10% |
| opposition half passes | 5% |
| ground duels | 7.5% |
| successful dribbles | 7.5% |

---

## Ataque/Defesa — B4

| Parâmetro | Valor | Status |
|---|---:|---|
| cap Perfil | ±2.000 | Recalibrável |
| multiplicador Perfil | 0.8 | Recalibrável |
| peso Perfil_pré limpo | 60% | Recalibrável |
| peso Perfil_grupos limpo | 40% | Recalibrável |

Índice ofensivo O:

| Métrica | Peso |
|---|---:|
| xG criado | 35% |
| chances claras | 20% |
| finalizações no alvo | 15% |
| gols feitos | 15% |
| finalizações | 10% |
| posse de bola | 5% |

Índice defensivo D:

| Métrica | Peso aproximado |
|---|---:|
| xG sofrido | 40% |
| chances claras cedidas | 23% |
| finalizações no alvo sofridas | 17% |
| gols sofridos | 17% |
| finalizações sofridas | 3% |

---

## Gols esperados — B4

| Parâmetro | Valor | Status |
|---|---:|---|
| `base` | 1.30 | Recalibrável |
| `k` | 0.18 | Recalibrável |
| `γ` | 0.15 | Recalibrável |
| `δ` | 0.00 | Recalibrável |
| `δ_max_sugerido` | 0.05 | Recalibrável |

Transformacao vigente do gap de TSI para jogos futuros e mata-mata:

```text
d = TSI_A - TSI_B
V(d) = sign(d) * min(3.00, 1.25 * |d|^0.60)

lambda_A = 1.30 * exp(0.18 * ( V(d) + profile_signal))
lambda_B = 1.30 * exp(0.18 * (-V(d) + profile_signal))

profile_signal = 0.25 * (Perfil_A + Perfil_B)
```

Observacao operacional:

```text
O B3 preserva a curva de base usada para auditar os jogos de grupo ja avaliados.
A curva sublinear acima e usada para projecoes futuras, mata-mata e dashboard.
```

---

## Elenco — B5

| Parâmetro | Valor | Status |
|---|---:|---|
| limiar setor crítico | −1.0 (z) | Recalibrável |
| `λ` penalidade setor crítico | 0.50 | Recalibrável |
| `λ_e` shrinkage elenco | 0.35 | Recalibrável |
| cap ajuste elenco | ±1.000 | Recalibrável |
| jogadores confiáveis mínimos | 22 | Operacional |
| cobertura confiável mínima | 80% | Operacional |
| faixa normal ajuste elenco | ±0.500 | Observação |
| idade média início mult. seleção | 26 | Recalibrável |
| idade média teto mult. seleção | 31 | Recalibrável |
| multiplicador máximo idade seleção | 2.30 | Recalibrável |

```text
valor_efetivo = valor_mercado · nível_clube
valor_seleção ← valor_seleção · mult_idade_seleção(idade_média)
valor_agregado_jogador = log(1 + valor_efetivo)
```

Seleções abaixo do mínimo de cobertura ficam com `ajuste_elenco = 0.000` até que
o cruzamento de valor de mercado seja completado.

---

## Odds — B6

| Parâmetro | Valor | Status |
|---|---:|---|
| cap ajuste odds | ±0.750 | Recalibrável |
| mercado base | passar de fase | Inicial |
| mercado topo | campeão | Inicial |
| devig campeão | normalização 48 seleções | Recalibrável |
| devig passar de fase | binário passar/não passar | Recalibrável |
| peso campeão vs passar | a definir | Recalibrável |

---

## Simulação — B7

| Parâmetro | Valor | Status |
|---|---:|---|
| modelo placar | Poisson puro | Inicial |
| Dixon-Coles `ρ` | desativado | Recalibrável |
| prorrogação | λ/3 | Recalibrável |
| `c_pen` | 0.010 | Recalibrável |
| clamp pênaltis | [0.40, 0.60] | Recalibrável |
| simulação rápida | 50.000 | Operacional |
| simulação estável | 200.000+ | Operacional |

---

## Validação — B9

| Parâmetro | Valor inicial |
|---|---|
| bins de calibração | 10 faixas |
| limiar para ativar Dixon-Coles | a definir |
| tolerância de divergência vs mercado | a definir |
| critério mínimo para aceitar ajuste | melhoria consistente em múltiplas métricas |

---

## Parâmetros mais sensíveis

```text
K
base
k
γ
cap Perfil
c_proc
peso pós-grupos 70/30
cap variação pós-grupos
λ_e elenco
cap odds
c_pen
```

Regra geral:

```text
se uma versão complexa melhora pouco,
manter a versão simples.
```
