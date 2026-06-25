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
Valor efetivo do jogador

valor_efetivo =
valor_mercado · nível_clube

Base simples: valor de mercado escalado pelo nível do clube, sem correção por idade,
minutagem ou liga no jogador. nível_clube ∈ [0, ~1.2].

Multiplicador coletivo de idade (por seleção)

O valor do elenco é então escalado por um limiar que cresce com a idade média do
elenco convocado, compensando o desconto de revenda do Transfermarkt em seleções
veteranas:

valor_seleção ←
valor_seleção · mult_idade_seleção(idade_média)

mult_idade_seleção vale 1.00 até a idade média de 26 anos, cresce linearmente até 2.30
aos 31 anos, e permanece em 2.30 acima disso. É uniforme dentro do time, então não
altera a comparação de equilíbrio entre setores.

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
Penalidade de setor crítico
media_z =
média dos z dos 4 setores

Só setores genuinamente fracos são punidos (não a mera falta de uniformidade). Um
setor é crítico quando z_setor < limiar_crítico; pune-se a profundidade abaixo da
linha, somada sobre todos os setores críticos:

déficit_crítico =
Σ_setor máx(0, limiar_crítico − z_setor)

Com:

limiar_crítico = −1.0   (≈ 16% pior do torneio no setor)
λ = 0.5
squad_score =
media_z − λ · déficit_crítico

Se nenhum setor está abaixo da linha, déficit = 0 e o time é ranqueado pelo talento
total (media_z). Assim, elencos fortes mas concentrados (ex.: ataque excelente, meio
mediano) não são penalizados por não serem uniformes.
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
