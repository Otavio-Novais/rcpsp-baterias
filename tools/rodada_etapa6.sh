#!/usr/bin/env bash
# Rodada da Etapa 6 (rodar da raiz do repositorio, com o notebook na tomada):
#   1. GA x BRKGA x RKO com orcamento de 50.000 cronogramas, decoder com FBI
#   2. o mesmo com o decoder so com SSGS (sem FBI)
#   3. Gurobi (600 s) nas 5 instancias J60, para comparar exato x aproximado
#      nos mesmos exemplares
# Ao final faz commit e push de results/ (mesmo se algum passo falhar).
#
# Uso:  systemd-inhibit --what=sleep:idle bash tools/rodada_etapa6.sh
# Duracao estimada: 10 a 20 min das metaheuristicas + ate ~55 min do Gurobi.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python}
LOG=results/rodada_etapa6_$(date +%Y%m%d_%H%M).log
status=0
{
  echo "== inicio $(date)"
  git pull --ff-only || true
  $PY tools/run_metaheuristics.py --budget 50000 || status=1
  $PY tools/run_metaheuristics.py --budget 50000 --fbi 0 || status=1
  $PY ampl/run_exact.py --set selecao_j60 --solver gurobi --time 600 || status=1
  echo "== fim $(date) (status $status)"
} 2>&1 | tee "$LOG"
git add results/
git commit -m "Rodada da Etapa 6: metaheuristicas com 50.000 cronogramas e Gurobi no J60" || true
git push || echo "push falhou: rode 'git push' manualmente"
