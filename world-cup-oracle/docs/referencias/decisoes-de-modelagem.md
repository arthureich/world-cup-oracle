# Decisões de Modelagem

Projeto: **Tactical Oracle**

Registro das decisões metodológicas e seus motivos.

---

## 1. Usar o ciclo da Copa

### Decisão

Usar o ciclo competitivo da Copa 2026:

```text
pós-Copa 2022 até pré-Copa 2026
```

### Motivo

Reduz complexidade de dados e foca no estado recente das seleções.

---

## 2. FIFA não entra diretamente no TSI

### Decisão

Pontos FIFA inicializam Elo, mas não entram diretamente no TSI.

### Motivo

Ranking FIFA, Elo e odds carregam sinais parecidos. Usar FIFA diretamente duplicaria informação.

---

## 3. TSI é força geral; Ataque/Defesa são derivados

```text
Ataque = TSI + Perfil
Defesa = TSI − Perfil
```

### Motivo

Evita parâmetros ofensivos/defensivos independentes demais para o volume de dados.

---

## 4. Perfil mede total de gols, não saldo

```text
saldo de gols → TSI/Elo
total de gols → Perfil
```

### Motivo

Saldo já está no eixo de força. Perfil mede jogo aberto/travado.

---

## 5. λ por função log-linear

```text
λ_A =
base · exp(k · (Ataque_A − Defesa_B))
```

### Motivo

Mantém λ positivo e conecta força, estilo, ataque e defesa de forma interpretável.

---

## 6. Poisson puro como MVP

### Decisão

Começar com Poisson independente.

### Motivo

É simples e interpretável. Dixon-Coles só entra se B9 provar necessidade.

---

## 7. Processo e resultado separados

### Decisão

B3 usa dois canais:

```text
PROCESSO  → xG e volume
RESULTADO → pontos reais
```

### Motivo

Evita inflar processo com variância de finalização.

---

## 8. Força do adversário entra pelo esperado

### Decisão

Sem termo separado de adversário no B3.

### Motivo

A força do adversário já está em `GD_esp`.

---

## 9. Cartão vermelho vira peso de confiabilidade

### Decisão

Usar minutos de desequilíbrio numérico.

### Motivo

Expulsão distorce xG, posse e volume dos dois lados.

---

## 10. Elenco é ajuste estrutural

```text
ajuste_elenco ∈ [−1.000, +1.000]
```

### Motivo

Elenco corrige, mas não domina o Elo.

---

## 11. Valor de mercado precisa de correção por idade

### Decisão

Usar curva de mercado e curva de habilidade.

```text
V_pico = valor_mercado / curva_mercado(idade)
V_atual = V_pico · curva_habilidade(idade)
```

### Motivo

Valor de mercado mede revenda, não só qualidade atual.

---

## 12. Usar log(1 + valor)

```text
valor_agregado_jogador =
log(1 + valor_efetivo)
```

### Motivo

Evita que 1 ou 2 estrelas dominem o elenco inteiro.

---

## 13. Goleiro separado

### Decisão

Setores:

```text
GOL
DEF
MEI
ATA
```

### Motivo

Goleiros podem ter valor de mercado subestimado.

---

## 14. Odds são ajuste leve

```text
ajuste_odds ∈ [−0.750, +0.750]
```

### Motivo

Mercado ajuda, mas não substitui o modelo.

---

## 15. B6 e B9 usam odds diferentes

```text
B6 → odds de longo prazo
B9 → odds jogo a jogo
```

### Motivo

Evita circularidade na validação.

---

## 16. Pênaltis quase 50/50

```text
P(A vence nos pênaltis) =
clamp(0.5 + c_pen · ΔTSI, 0.40, 0.60)
```

### Motivo

Força ajuda pouco em pênaltis, mas não deve dominar.

---

## 17. Fair play não é simulado pré-Copa

### Decisão

Pré-Copa usa ranking FIFA como desempate residual.  
Durante a Copa, usar fair play real se disponível.

---

## 18. Anexo C como dado

### Decisão

Carregar tabela oficial de combinações dos melhores terceiros.

### Motivo

Evita erro de chaveamento.

---

## 19. B9 protege contra overfitting

### Decisão

Só aceitar ajustes com melhoria consistente.

### Motivo

Evita calibrar demais para torneios passados.

---

## 20. Stack simples primeiro

### Decisão

Começar com:

```text
Python
Polars
DuckDB
Parquet
NumPy/SciPy
Streamlit
```

### Motivo

O projeto é analítico e local no MVP.
