"""Gera as linhas da Tabela 1 da Etapa 6 (exato x RKO por instancia) a partir dos CSVs.

Uso (raiz do repositorio): python3 relatorios/etapa6/gera_tabela.py > relatorios/etapa6/tabela1_linhas.tex
"""
import csv
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import psplib  # noqa: E402

EXATO = ["results/exact_selecao_j30_gurobi_D.csv", "results/exact_selecao_j60_gurobi_D.csv"]
RKO_TEMPO = "results/mh_20261102_2306/Stats_RKO.csv"
RKO_ORC = "results/mh_20261103_0825_b50000/Stats_RKO.csv"


def num(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def load_mh(path):
    R = {}
    for r in csv.DictReader(open(ROOT / path)):
        R.setdefault(r["instance"].split("/")[-1], []).append(r)
    return R


ex = {}
for f in EXATO:
    for r in csv.DictReader(open(ROOT / f)):
        ex[r["file"].split("/")[-1]] = r
T, B = load_mh(RKO_TEMPO), load_mh(RKO_ORC)

agg = {k: {"J30": [], "J60": []} for k in ("g_rpd", "g_t", "t_best", "t_mean", "t_t", "b_best", "b_mean", "b_t")}
for i, e in ex.items():
    ref = int(e["ref"])
    grp = "J30" if i.startswith("J30") else "J60"
    g = int(e["cmax"])
    tb = [int(x["cmax"]) for x in T[i]]
    bb = [int(x["cmax"]) for x in B[i]]
    t_t = st.mean(float(x["time_total"]) for x in T[i])
    b_t = st.mean(float(x["time_total"]) for x in B[i])
    rpd = lambda c: 100 * (c - ref) / ref  # noqa: E731
    for k, v in (("g_rpd", rpd(g)), ("g_t", float(e["time_s"])), ("t_best", rpd(min(tb))),
                 ("t_mean", rpd(st.mean(tb))), ("t_t", t_t), ("b_best", rpd(min(bb))),
                 ("b_mean", rpd(st.mean(bb))), ("b_t", b_t)):
        agg[k][grp].append(v)
    bold = lambda c: f"\\textbf{{{c}}}" if c == ref else str(c)  # noqa: E731
    dag = "$^\\dagger$" if e["status"] != "OTIMO" else ""
    name = psplib.psplib_name(i).replace("_", "\\_")
    print(f"{name} & {ref} & {bold(g)}{dag} & {num(float(e['time_s']))} & {bold(min(tb))} & {num(st.mean(tb))} & "
          f"{num(t_t, 2)} & {bold(min(bb))} & {num(st.mean(bb))} & {num(b_t, 2)} \\\\")
    if i == "J30_30_2.dzn":
        print("\\midrule")
print("\\midrule")
for grp in ("J30", "J60"):
    a = {k: st.mean(v[grp]) for k, v in agg.items()}
    print(f"RPD / tempo {grp} & & {num(a['g_rpd'], 2)}\\% & {num(a['g_t'])} & {num(a['t_best'], 2)}\\% & "
          f"{num(a['t_mean'], 2)}\\% & {num(a['t_t'], 2)} & {num(a['b_best'], 2)}\\% & {num(a['b_mean'], 2)}\\% & "
          f"{num(a['b_t'], 2)} \\\\")
