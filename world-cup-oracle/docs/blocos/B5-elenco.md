B5 — Elenco
Objetivo

O B5 corrige o TSI quando o Elo/TSI subestima ou superestima a força real da seleção por causa da qualidade atual do elenco convocado.

B5 = ajuste estrutural de qualidade do elenco
Fontes
valor de mercado: Transfermarkt
minutagem / nível de clube: FotMob ou FBref

Escopo:

somente os 26 convocados
sem modelar lesões/ausências separadamente
roda após a convocação
funcionamento automático
Valor de pico
V_pico =
valor_mercado / curva_mercado(idade)
Valor atual
V_atual =
V_pico · curva_habilidade(idade)
Correção de potencial

Para jogadores com idade ≤ 22:

V_atual ←
V_atual · (0.6 + 0.4 · status)

Onde:

status ∈ [0, 1]

status mede minutagem recente ponderada por nível do clube/liga.

Valor efetivo
valor_efetivo =
V_atual após correção de potencial

Antes de agregar:

valor_agregado_jogador =
log(1 + valor_efetivo)

Isso evita que 1 ou 2 estrelas dominem o elenco inteiro.

Setores
GOL
DEF
MEI
ATA

Para cada setor:

z_setor =
padronizar valor do setor entre as 48 seleções
Penalidade de desbalanceamento
media_z =
média dos z dos 4 setores
min_z =
menor z_setor
penalidade_balanco =
β · (media_z − min_z)

Com:

β = 0.30
squad_score =
media_z − penalidade_balanco
TSI implícito de elenco
TSI_elenco_implícito =
padronizar squad_score
para média e desvio do TSI_base
Ajuste de elenco
ajuste_elenco =
clamp(
  λ_e · (TSI_elenco_implícito − TSI_base),
  −1.000,
  +1.000
)

Com:

λ_e = 0.35
TSI_modelo =
TSI_base + ajuste_elenco
