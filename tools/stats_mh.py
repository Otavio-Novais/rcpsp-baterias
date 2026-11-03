"""Testes estatisticos do experimento das metaheuristicas (com e sem FBI).

Uso: python3 tools/stats_mh.py results/mh_<data> results/mh_<data>_semFBI [--out results/analise_mh.md]

- Friedman sobre o RPD medio por instancia (blocos = instancias), por conjunto (J30, J60, todas)
- Wilcoxon pareado (por instancia) entre pares de metodos, com correcao de Holm
- Mann-Whitney por metodo: com FBI x sem FBI (todas as execucoes)
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
METHODS = ["GA", "BRKGA", "RKO"]


def load_ref():
    ref = {}
    for f in ("reference_j30.csv", "reference_j60.csv"):
        for r in csv.DictReader(open(ROOT / "results" / f)):
            ref[r["instance"]] = int(r["ub"])
    return ref


def load(d: Path, ref):
    runs = defaultdict(list)
    for m in METHODS:
        for r in csv.DictReader(open(d / f"Stats_{m}.csv")):
            name = r["instance"].split("/")[-1]
            c = int(r["cmax"])
            runs[(name, m)].append({"rpd": 100 * (c - ref[name]) / ref[name], "sched": int(r["schedules"]),
                                    "tt": float(r["time_total"]), "ttb": float(r["time_to_best"])})
    return runs


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj


def block(R, insts, title):
    L = [f"### {title}", "", "| Conjunto | " + " | ".join(f"{m} RPD médio / no ótimo" for m in METHODS) + " | Friedman p |",
         "|---|" + "---:|" * len(METHODS) + "---:|"]
    for sub, flt in (("J30", "J30"), ("J60", "J60"), ("Todas", "")):
        I = [i for i in insts if i.startswith(flt)]
        means = {m: [st.mean(x["rpd"] for x in R[(i, m)]) for i in I] for m in METHODS}
        hits = {m: sum(x["rpd"] == 0 for i in I for x in R[(i, m)]) for m in METHODS}
        p = stats.friedmanchisquare(*means.values()).pvalue
        L.append(f"| {sub} | " + " | ".join(f"{st.mean(means[m]):.2f}% / {hits[m]}/{10 * len(I)}" for m in METHODS)
                 + f" | {p:.3f} |")
    pairs = [("RKO", "GA"), ("RKO", "BRKGA"), ("GA", "BRKGA")]
    ps = []
    for a, b in pairs:
        ma = [st.mean(x["rpd"] for x in R[(i, a)]) for i in insts]
        mb = [st.mean(x["rpd"] for x in R[(i, b)]) for i in insts]
        ps.append(stats.wilcoxon(ma, mb).pvalue if any(x != y for x, y in zip(ma, mb)) else 1.0)
    adj = holm(ps)
    L += ["", "Wilcoxon pareado por instância (15 instâncias), p bruto → p ajustado (Holm): " +
          "; ".join(f"{a}×{b}: {p:.3f} → {q:.3f}" for (a, b), p, q in zip(pairs, ps, adj)), ""]
    tot = {m: (sum(x["sched"] for i in insts for x in R[(i, m)]), sum(x["tt"] for i in insts for x in R[(i, m)]))
           for m in METHODS}
    if all(t > 0 for _, t in tot.values()):
        L.append("Cronogramas avaliados por segundo (9 threads): " +
                 ", ".join(f"{m} {c / t:,.0f}".replace(",", ".") for m, (c, t) in tot.items()) + ".")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("com_fbi")
    ap.add_argument("sem_fbi")
    ap.add_argument("--out")
    a = ap.parse_args()
    ref = load_ref()
    C, S = load(Path(a.com_fbi), ref), load(Path(a.sem_fbi), ref)
    insts = sorted({k[0] for k in C})
    L = ["## Análise estatística das metaheurísticas", ""]
    L += block(C, insts, "Decoder com FBI") + [""] + block(S, insts, "Decoder sem FBI (só SSGS)") + [""]
    L += ["### Efeito do FBI (Mann-Whitney, todas as execuções)", "",
          "| Método | J30 com / sem FBI | p | J60 com / sem FBI | p |", "|---|---:|---:|---:|---:|"]
    for m in METHODS:
        row = f"| {m} |"
        for flt in ("J30", "J60"):
            x = [r["rpd"] for i in insts if i.startswith(flt) for r in C[(i, m)]]
            y = [r["rpd"] for i in insts if i.startswith(flt) for r in S[(i, m)]]
            row += f" {st.mean(x):.2f}% / {st.mean(y):.2f}% | {stats.mannwhitneyu(x, y).pvalue:.4f} |"
        L.append(row)
    md = "\n".join(L) + "\n"
    print(md)
    if a.out:
        Path(a.out).write_text(md)


if __name__ == "__main__":
    sys.exit(main())
