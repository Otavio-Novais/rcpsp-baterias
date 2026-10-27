"""Valores de referencia (otimo ou melhor limitante) via OR-Tools CP-SAT.

Uso: python3 tools/reference_cpsat.py rko/Instances/RCPSP/j30 --time 10 --out results/reference_j30.csv

Serve apenas para VALIDAR o decoder do RKO e calcular o RPD quando a tabela
oficial da PSPLIB (j30opt.sm / j60hrs.sm) nao estiver a mao. Os valores devem
ser conferidos com a PSPLIB antes de entrar no artigo. O metodo exato do
trabalho continua sendo o modelo PLIM tempo-indexado em AMPL.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).parent))
import psplib  # noqa: E402


def solve(inst: psplib.Instance, time_limit: float, workers: int):
    m = cp_model.CpModel()
    H = inst.horizon
    s = [m.NewIntVar(0, H - inst.dur[j], f"s{j}") for j in range(inst.J)]
    itv = [m.NewFixedSizeIntervalVar(s[j], inst.dur[j], f"i{j}") for j in range(inst.J)]
    for j in range(inst.J):
        for q in inst.succ[j]:
            m.Add(s[q] >= s[j] + inst.dur[j])
    for k in range(inst.K):
        js = [j for j in range(inst.J) if inst.req[j][k] > 0]
        m.AddCumulative([itv[j] for j in js], [inst.req[j][k] for j in js], inst.cap[k])
    cmax = m.NewIntVar(inst.lower_bound(), H, "cmax")
    for j in range(inst.J):
        m.Add(cmax >= s[j] + inst.dur[j])
    m.Minimize(cmax)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    t0 = time.time()
    st = solver.Solve(m)
    t = time.time() - t0
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, int(solver.BestObjectiveBound()), "UNKNOWN", t
    return (int(solver.ObjectiveValue()), int(solver.BestObjectiveBound()),
            "OPTIMAL" if st == cp_model.OPTIMAL else "FEASIBLE", t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--time", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pattern", default="*.dzn")
    a = ap.parse_args()

    files = sorted(Path(a.folder).glob(a.pattern),
                   key=lambda p: psplib.parse_name(p.name)[1:])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "psplib_name", "group", "NC", "RF", "RS", "J", "K",
                    "horizon", "lb_cpm", "lb_res", "ub", "lb", "status", "time_s"])
        for p in files:
            inst = psplib.read(p)
            _, g, _ = psplib.parse_name(p.name)
            nc, rf, rs = psplib.progen_params(g)
            ub, lb, status, t = solve(inst, a.time, a.workers)
            w.writerow([p.name, psplib.psplib_name(p.name), g, nc, rf, rs, inst.J, inst.K,
                        inst.horizon, inst.lb_cpm(), inst.lb_resource(), ub, lb, status, f"{t:.2f}"])
            f.flush()
            print(f"{p.name:14s} ub={ub} lb={lb} {status} {t:.2f}s", flush=True)


if __name__ == "__main__":
    main()
