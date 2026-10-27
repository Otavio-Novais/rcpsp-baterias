"""Valida a FORMULACAO de ampl/rcpsp.mod sem AMPL: monta o mesmo modelo,
restricao por restricao, com o HiGHS (highspy) e confere contra a referencia.

Uso: python3 tools/validate_exact_highs.py --set selecao_j30 --time 120 --form D
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import highspy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import exact_data as ed  # noqa: E402
import psplib  # noqa: E402
from experiments import INST_DIR, SETS, read_reference  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def solve_highs(d: ed.ExactData, form: str, time_limit: float, relax: bool = False):
    J = range(1, d.n + 1)
    idx: dict[tuple[int, int], int] = {}
    for j in J:
        for t in range(d.ES[j], d.LS[j] + 1):
            idx[(j, t)] = len(idx)
    nv = len(idx)
    cost = np.zeros(nv)
    for t in range(d.ES[d.n], d.LS[d.n] + 1):
        cost[idx[(d.n, t)]] = t                                     # (1)

    rows = []                                                       # (lb, ub, {col: coef})

    def add(lo, hi, coefs):
        rows.append((lo, hi, coefs))

    for j in J:                                                     # (2)
        add(1, 1, {idx[(j, t)]: 1.0 for t in range(d.ES[j], d.LS[j] + 1)})

    for j in J:
        for i in d.P[j]:
            if form == "A":                                         # (3a)
                c: dict[int, float] = {}
                for t in range(d.ES[j], d.LS[j] + 1):
                    c[idx[(j, t)]] = c.get(idx[(j, t)], 0) + t
                for t in range(d.ES[i], d.LS[i] + 1):
                    c[idx[(i, t)]] = c.get(idx[(i, t)], 0) - t
                add(d.p[i], highspy.kHighsInf, c)
            else:                                                   # (3b)
                for t in range(d.ES[j], d.LS[j] + 1):
                    c = {idx[(j, s)]: 1.0 for s in range(d.ES[j], t + 1)}
                    for s in range(d.ES[i], min(d.LS[i], t - d.p[i]) + 1):
                        c[idx[(i, s)]] = c.get(idx[(i, s)], 0) - 1.0
                    add(-highspy.kHighsInf, 0, c)

    for k in d.K:                                                   # (4)
        for tau in range(d.H):
            c = {}
            for j in J:
                rjk = d.r.get((j, k), 0)
                if rjk <= 0:
                    continue
                for t in range(max(d.ES[j], tau - d.p[j] + 1), min(d.LS[j], tau) + 1):
                    c[idx[(j, t)]] = rjk
            if c:
                add(-highspy.kHighsInf, d.R[k], c)

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", float(time_limit))
    h.setOptionValue("threads", 2)
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = nv, len(rows)
    lp.col_cost_ = cost
    lp.col_lower_ = np.zeros(nv)
    lp.col_upper_ = np.ones(nv)
    lp.row_lower_ = np.array([r[0] for r in rows], dtype=float)
    lp.row_upper_ = np.array([r[1] for r in rows], dtype=float)
    # matriz por colunas (CSC)
    cols: list[list[tuple[int, float]]] = [[] for _ in range(nv)]
    for ri, (_, _, c) in enumerate(rows):
        for col, v in c.items():
            if v != 0:
                cols[col].append((ri, v))
    start, index, value = [0], [], []
    for col in cols:
        for ri, v in col:
            index.append(ri)
            value.append(v)
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = start, index, value
    if not relax:
        lp.integrality_ = [highspy.HighsVarType.kInteger] * nv
    h.passModel(lp)
    if not relax and d.start:                     # MIP start = cronograma heuristico
        x0 = np.zeros(nv)
        for j, t in d.start.items():
            x0[idx[(j, t)]] = 1.0
        sol0 = highspy.HighsSolution()
        sol0.col_value = list(x0)
        sol0.value_valid = True
        h.setSolution(sol0)
    t0 = time.time()
    h.run()
    el = time.time() - t0
    info = h.getInfo()
    status = h.modelStatusToString(h.getModelStatus())
    if relax:
        return info.objective_function_value, el
    sol = h.getSolution().col_value
    x = {key: sol[i] for key, i in idx.items()}
    return status, info.objective_function_value, info.mip_dual_bound, el, x, nv, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instances", nargs="*")
    ap.add_argument("--set", choices=sorted(SETS))
    ap.add_argument("--time", type=float, default=120)
    ap.add_argument("--form", choices=["D", "A"], default="D")
    ap.add_argument("--ref", nargs="+", default=[str(ROOT / "results/reference_j30.csv"),
                                                  str(ROOT / "results/reference_j60.csv")])
    ap.add_argument("--h-ref", action="store_true",
                    help="usa H = otimo de referencia (modelo menor; teste de correcao da formulacao)")
    ap.add_argument("--out")
    a = ap.parse_args()
    insts = list(a.instances) + (SETS[a.set] if a.set else [])
    ref = read_reference([r for r in a.ref if Path(r).exists()])

    out_rows = []
    for rel in insts:
        inst = psplib.read(INST_DIR / rel)
        rr0 = ref.get(Path(rel).name) or ref.get(Path(rel).stem)
        if a.h_ref and rr0 and rr0["status"] == "OPTIMAL":
            d = ed.build(inst, horizon=int(rr0["ub"]))
        else:
            d = ed.build(inst)
        lpv, lpt = solve_highs(d, a.form, a.time, relax=True)
        status, obj, bound, el, x, nv, nr = solve_highs(d, a.form, a.time)
        ok, msg = ed.verify(d, x, obj)
        rr = ref.get(Path(rel).name) or ref.get(Path(rel).stem)
        refv = int(rr["ub"]) if rr and rr["status"] == "OPTIMAL" else None
        flag = ""
        if status == "Optimal" and refv is not None and np.isfinite(obj) and round(obj) != refv:
            flag = "  <-- DIFERENTE DA REFERENCIA"
        print(f"{Path(rel).stem:12s} form={a.form} H={d.H:4d} vars={nv:5d} rows={nr:6d} LP={lpv:7.2f} "
              f"{status:12s} obj={obj:6.0f} bound={bound:7.2f} ref={refv} t={el:6.1f}s verif={msg}{flag}", flush=True)
        out_rows.append(dict(instance=Path(rel).name, form=a.form, H=d.H, rule=d.rule, lb=d.lb, vars=nv, rows=nr,
                             lp=round(lpv, 3), status=status, cmax=round(obj) if np.isfinite(obj) else '', bound=round(bound, 3),
                             ref=refv, time_s=round(el, 2), verified=msg))
    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
            w.writeheader()
            w.writerows(out_rows)


if __name__ == "__main__":
    main()
