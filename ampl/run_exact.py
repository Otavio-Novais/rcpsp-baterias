"""Etapa 5 - metodo exato: resolve ampl/rcpsp.mod via amplpy para cada instancia.

Exemplos (a partir da raiz do repositorio):
  python ampl/run_exact.py --set selecao_j30 --solver gurobi --time 600
  python ampl/run_exact.py j30/J30_13_1.dzn --solver cplex --time 60 --verbose
  python ampl/run_exact.py --set selecao_j30 --dry-run          # so gera os .dat

Para cada instancia:
  1. H = melhor makespan do SSGS com regras de prioridade (+FBI) -> limitante superior
  2. janelas [ES, LS] pelo CPM; grava ampl/data/<instancia>.dat
  3. PLIM com limite de tempo (MIP start = heuristica); le makespan,
     limitante inferior (bestbound) e tempo
  4. confere a solucao do solver com um verificador independente do modelo
  5. (opcional) relaxacao linear -> coluna LP
  6. grava uma linha em results/exact_<set>_<solver>_<form>.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import exact_data as ed  # noqa: E402
import psplib  # noqa: E402
from experiments import INST_DIR, SETS, read_reference  # noqa: E402

MODEL = ROOT / "ampl" / "rcpsp.mod"


def new_ampl():
    from amplpy import AMPL
    try:                                   # modulos instalados via "amplpy.modules install"
        from amplpy import modules
        modules.load()
    except Exception:
        pass
    return AMPL()


def solve_instance(rel: str, a, ref: dict) -> dict:
    inst = psplib.read(INST_DIR / rel)
    t0 = time.time()
    d = ed.build(inst, use_fbi=not a.no_fbi)
    t_heur = time.time() - t0
    dat = ROOT / "ampl" / "data" / f"{psplib.psplib_name(Path(rel).name)}.dat"
    ed.write_dat(d, dat)

    rr = ref.get(Path(rel).name) or ref.get(Path(rel).stem)
    row = dict(instance=psplib.psplib_name(Path(rel).name), file=rel, J=inst.J, K=inst.K,
               ref=int(rr["ub"]) if rr and rr["ub"] not in ("", "None") else "",
               ref_status=rr["status"] if rr else "",
               lb_trivial=d.lb, H=d.H, H_rule=d.rule, t_heur=round(t_heur, 3),
               binaries=d.n_binaries, form=a.form, solver=a.solver)
    if a.dry_run:
        return row

    ampl = new_ampl()
    ampl.read(str(MODEL))
    ampl.read_data(str(dat))
    ampl.param["formul"] = a.form
    ampl.option["solver"] = a.solver
    opts = f"lim:time={a.time} mip:bestbound=1"
    if a.verbose:
        opts += " outlev=1"
    if a.solver_options:
        opts += " " + a.solver_options
    ampl.option[f"{a.solver}_options"] = opts

    # PLIM primeiro: os valores iniciais de x (cronograma da heuristica, no .dat)
    # sao o MIP start. Resolver a LP antes trocaria esse ponto inicial pela
    # solucao fracionaria da relaxacao.
    ampl.solve()
    status = ampl.solve_result                       # solved | limit | infeasible | failure ...
    t_solve = ampl.get_value("_solve_elapsed_time")
    obj = ampl.get_objective("Makespan").value()
    try:
        bound = ampl.get_value("Makespan.bestbound")
    except Exception:
        bound = float("nan")
    if status == "solved":
        bound = obj
    xs = {(int(j), int(t)): v for j, t, v in ampl.get_variable("x").get_values().to_list()}
    ok, msg = ed.verify(d, xs, obj) if xs and status in ("solved", "limit") else (False, "sem solucao")
    nvars, ncons = int(ampl.get_value("_nvars")), int(ampl.get_value("_ncons"))

    # relaxacao linear (forca da formulacao), depois do PLIM
    lp = ""
    if not a.no_lp:
        ampl.option["relax_integrality"] = 1
        ampl.solve()
        if ampl.solve_result == "solved":
            lp = round(ampl.get_objective("Makespan").value(), 3)
        ampl.option["relax_integrality"] = 0

    cmax = round(obj) if ok else ""
    gap = round(100.0 * (obj - bound) / obj, 2) if ok and not math.isnan(bound) and obj > 0 else ""
    row.update(status="OTIMO" if status == "solved" else status.upper(), cmax=cmax,
               bound=round(bound, 3) if not math.isnan(bound) else "", gap_pct=gap, lp=lp,
               time_s=round(t_solve, 2), vars=nvars, cons=ncons, verified=msg)
    if ok and row["ref"] != "" and row["ref_status"] == "OPTIMAL" and status == "solved" and cmax != row["ref"]:
        row["verified"] = f"ERRO: otimo {cmax} difere da referencia {row['ref']}"
    ampl.close()
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instances", nargs="*", help="caminhos relativos a rko/Instances/RCPSP (ex. j30/J30_13_1.dzn)")
    ap.add_argument("--set", choices=sorted(SETS))
    ap.add_argument("--solver", default="gurobi", help="gurobi | cplex | xpress | highs")
    ap.add_argument("--time", type=int, default=600, help="limite de tempo por instancia (s)")
    ap.add_argument("--form", choices=["D", "A"], default="D", help="precedencia Desagregada ou Agregada")
    ap.add_argument("--solver-options", default="", help='opcoes extras do solver, ex. "threads=4"')
    ap.add_argument("--no-lp", action="store_true", help="nao calcula a relaxacao linear")
    ap.add_argument("--no-fbi", action="store_true", help="H so com regras de prioridade (sem FBI)")
    ap.add_argument("--dry-run", action="store_true", help="so gera os .dat e mostra o tamanho do modelo")
    ap.add_argument("--verbose", action="store_true", help="mostra o log do solver")
    ap.add_argument("--out", help="CSV de saida (padrao: results/exact_<set>_<solver>_<form>.csv)")
    a = ap.parse_args()

    insts = list(a.instances) + (SETS[a.set] if a.set else [])
    if not insts:
        ap.error("informe instancias ou --set")
    refs = [p for p in (ROOT / "results/reference_j30.csv", ROOT / "results/reference_j60.csv") if p.exists()]
    ref = read_reference([str(p) for p in refs])
    out = Path(a.out) if a.out else ROOT / "results" / f"exact_{a.set or 'custom'}_{a.solver}_{a.form}.csv"

    rows = []
    for rel in insts:
        row = solve_instance(rel, a, ref)
        rows.append(row)
        if a.dry_run:
            print(f"{row['instance']:10s} H={row['H']:4d} ({row['H_rule']}) LB={row['lb_trivial']:4d} "
                  f"binarias={row['binaries']:6d}")
            continue
        print(f"{row['instance']:10s} {row['status']:8s} Cmax={row['cmax']!s:>4} LB={row['bound']!s:>8} "
              f"gap={row['gap_pct']!s:>6}% LP={row['lp']!s:>8} t={row['time_s']:7.1f}s ref={row['ref']} "
              f"[{row['verified']}]", flush=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="") as f:          # regrava a cada instancia (seguro se interromper)
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    if not a.dry_run:
        bad = [r for r in rows if r["verified"] != "ok"]
        print(f"\n{len(rows)} instancias -> {out}")
        if bad:
            print(f"ATENCAO: {len(bad)} instancia(s) sem solucao verificada: " + ", ".join(r["instance"] for r in bad))


if __name__ == "__main__":
    main()
