## Análise estatística das metaheurísticas

### Decoder com FBI

| Conjunto | GA RPD médio / no ótimo | BRKGA RPD médio / no ótimo | RKO RPD médio / no ótimo | Friedman p |
|---|---:|---:|---:|---:|
| J30 | 0.74% / 65/100 | 0.66% / 70/100 | 0.78% / 66/100 | 0.148 |
| J60 | 3.63% / 0/50 | 4.10% / 0/50 | 3.83% / 0/50 | 0.241 |
| Todas | 1.71% / 65/150 | 1.81% / 70/150 | 1.80% / 66/150 | 0.273 |

Wilcoxon pareado por instância (15 instâncias), p bruto → p ajustado (Holm): RKO×GA: 0.401 → 1.000; RKO×BRKGA: 0.735 → 1.000; GA×BRKGA: 0.612 → 1.000

Cronogramas avaliados por segundo (9 threads): GA 90.463, BRKGA 94.658, RKO 89.513.

### Decoder sem FBI (só SSGS)

| Conjunto | GA RPD médio / no ótimo | BRKGA RPD médio / no ótimo | RKO RPD médio / no ótimo | Friedman p |
|---|---:|---:|---:|---:|
| J30 | 1.85% / 47/100 | 2.07% / 41/100 | 1.84% / 48/100 | 0.289 |
| J60 | 9.09% / 0/50 | 10.39% / 0/50 | 9.59% / 0/50 | 0.041 |
| Todas | 4.26% / 47/150 | 4.84% / 41/150 | 4.43% / 48/150 | 0.035 |

Wilcoxon pareado por instância (15 instâncias), p bruto → p ajustado (Holm): RKO×GA: 0.260 → 0.260; RKO×BRKGA: 0.050 → 0.100; GA×BRKGA: 0.006 → 0.018

Cronogramas avaliados por segundo (9 threads): GA 482.698, BRKGA 498.778, RKO 530.199.

### Efeito do FBI (Mann-Whitney, todas as execuções)

| Método | J30 com / sem FBI | p | J60 com / sem FBI | p |
|---|---:|---:|---:|---:|
| GA | 0.74% / 1.85% | 0.0003 | 3.63% / 9.09% | 0.0000 |
| BRKGA | 0.66% / 2.07% | 0.0000 | 4.10% / 10.39% | 0.0000 |
| RKO | 0.78% / 1.84% | 0.0007 | 3.83% / 9.59% | 0.0000 |
