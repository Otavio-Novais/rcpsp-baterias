## Análise estatística das metaheurísticas

### Decoder com FBI

| Conjunto | GA RPD médio / no ótimo | BRKGA RPD médio / no ótimo | RKO RPD médio / no ótimo | Friedman p |
|---|---:|---:|---:|---:|
| J30 | 0.29% / 78/100 | 0.24% / 81/100 | 0.28% / 79/100 | 0.607 |
| J60 | 0.92% / 16/50 | 1.00% / 14/50 | 1.00% / 15/50 | 0.223 |
| Todas | 0.50% / 94/150 | 0.49% / 95/150 | 0.52% / 94/150 | 0.807 |

Wilcoxon pareado por instância (15 instâncias), p bruto → p ajustado (Holm): RKO×GA: 0.285 → 0.855; RKO×BRKGA: 1.000 → 1.000; GA×BRKGA: 1.000 → 1.000

Cronogramas avaliados por segundo (9 threads): GA 115.645, BRKGA 107.605, RKO 118.157.

### Decoder sem FBI (só SSGS)

| Conjunto | GA RPD médio / no ótimo | BRKGA RPD médio / no ótimo | RKO RPD médio / no ótimo | Friedman p |
|---|---:|---:|---:|---:|
| J30 | 0.43% / 71/100 | 0.51% / 66/100 | 0.38% / 75/100 | 0.584 |
| J60 | 2.00% / 8/50 | 2.07% / 4/50 | 1.69% / 11/50 | 0.174 |
| Todas | 0.95% / 79/150 | 1.03% / 70/150 | 0.82% / 86/150 | 0.122 |

Wilcoxon pareado por instância (15 instâncias), p bruto → p ajustado (Holm): RKO×GA: 0.046 → 0.128; RKO×BRKGA: 0.043 → 0.128; GA×BRKGA: 0.575 → 0.575

Cronogramas avaliados por segundo (9 threads): GA 548.211, BRKGA 504.853, RKO 619.271.

### Efeito do FBI (Mann-Whitney, todas as execuções)

| Método | J30 com / sem FBI | p | J60 com / sem FBI | p |
|---|---:|---:|---:|---:|
| GA | 0.29% / 0.43% | 0.1813 | 0.92% / 2.00% | 0.0000 |
| BRKGA | 0.24% / 0.51% | 0.0039 | 1.00% / 2.07% | 0.0000 |
| RKO | 0.28% / 0.38% | 0.3939 | 1.00% / 1.69% | 0.0085 |
