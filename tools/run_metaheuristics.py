"""Experimento das metaheuristicas: GA x BRKGA x RKO com o mesmo decoder.

Uso (a partir da raiz do repositorio):
  python3 tools/run_metaheuristics.py                       # padrao: J30 10 s, J60 30 s, 10 execucoes
  python3 tools/run_metaheuristics.py --runs 3 --time-j30 3 --time-j60 5   # teste rapido
  python3 tools/run_metaheuristics.py --fbi 0               # decoder sem FBI (so SSGS)
  python3 tools/run_metaheuristics.py --budget 50000        # orcamento de 50.000 cronogramas por execucao

O que faz:
  1. compila o RKO, se preciso;
  2. gera os cenarios das selecoes J30 e J60;
  3. roda cada metodo (GA = 6, BRKGA = 0, RKO = 9) em cada selecao, no modo D = 0;
  4. copia as saidas para results/mh_<data>/ e grava:
       summary.csv     uma linha por instancia x metodo (RPD, acertos, cronogramas ate o melhor...)
       comparison.md   tabela comparativa pronta para o relatorio/artigo
       machine.txt     CPU, nucleos e configuracao do experimento

Todos os metodos usam o mesmo decoder (chaves -> lista topologica -> SSGS + FBI),
o mesmo tempo, as mesmas 9 threads e a mesma maquina: a diferenca medida e a da
estrategia de busca.
"""
from __future__ import annotations

import argparse
import csv
import os
import platform
import shutil
import statistics as st
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import experiments as ex  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "rko" / "Program"
RES = ROOT / "rko" / "Results"
METHODS = {"GA": 6, "BRKGA": 0, "RKO": 9, "SA": 1, "GRASP": 2, "ILS": 3, "VNS": 4, "PSO": 5, "LNS": 7,
           "BRKGA_CS": 8}


def cpu_name() -> str:
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def build(fbi: int):
    """Compila o RKO. fbi=1 -> runTest (Makefile); fbi=0 -> runTest_nofbi (decoder sem FBI)."""
    src = PROG / "Problem" / "Problem.h"
    if fbi:
        exe = PROG / ("runTest.exe" if os.name == "nt" else "runTest")
        if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
            print("compilando o RKO...", flush=True)
            subprocess.run(["make", "rebuild"], cwd=PROG, check=True, stdout=subprocess.DEVNULL)
    else:
        exe = PROG / ("runTest_nofbi.exe" if os.name == "nt" else "runTest_nofbi")
        if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
            print("compilando o RKO sem FBI...", flush=True)
            subprocess.run(["g++", "-std=c++20", "-O3", "-fopenmp", "-DRCPSP_FBI=0", "-o", exe.name,
                            "Main/main.cpp"], cwd=PROG, check=True)
    return exe


def comparison_md(summary_csv: Path, methods: list[str]) -> str:
    rows = list(csv.DictReader(open(summary_csv)))
    by = {(r["instance"], r["mh"]): r for r in rows}
    insts = list(dict.fromkeys(r["instance"] for r in rows))
    L = ["| Instância | Ótimo | " + " | ".join(f"{m} RPD médio (acertos)" for m in methods) + " |",
         "|---|---:|" + "|".join("---:" for _ in methods) + "|"]
    for i in insts:
        ref = next((by[(i, m)]["ref"] for m in methods if (i, m) in by), "")
        cells = []
        for m in methods:
            r = by.get((i, m))
            cells.append(f"{float(r['rpd_mean']):.2f}% ({r['hits']}/{r['runs']})" if r else "--")
        name = i.replace(".dzn", "").replace(".sm", "")
        L.append(f"| {name} | {ref} | " + " | ".join(cells) + " |")

    L += ["", "| Métrica | " + " | ".join(methods) + " |", "|---|" + "|".join("---:" for _ in methods) + "|"]

    def agg(m, key, fn):
        v = [float(by[(i, m)][key]) for i in insts if (i, m) in by and by[(i, m)][key] not in ("", "nan")]
        return fn(v) if v else float("nan")

    def hits(m):
        h = sum(int(by[(i, m)]["hits"]) for i in insts if (i, m) in by and by[(i, m)]["hits"] != "")
        n = sum(int(by[(i, m)]["runs"]) for i in insts if (i, m) in by)
        return f"{h}/{n} ({100 * h / n:.0f}%)" if n else "--"

    L.append("| RPD médio (%) | " + " | ".join(f"{agg(m, 'rpd_mean', st.mean):.2f}" for m in methods) + " |")
    L.append("| RPD da melhor execução (%) | " + " | ".join(f"{agg(m, 'rpd_best', st.mean):.2f}" for m in methods) + " |")
    L.append("| Execuções no ótimo | " + " | ".join(hits(m) for m in methods) + " |")
    L.append("| Cronogramas até o melhor (média) | " + " | ".join(f"{agg(m, 'schedules_to_best_mean', st.mean):,.0f}" for m in methods) + " |")
    L.append("| Tempo até o melhor (s, média) | " + " | ".join(f"{agg(m, 'time_to_best_mean', st.mean):.2f}" for m in methods) + " |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--methods", nargs="+", default=["GA", "BRKGA", "RKO"], choices=sorted(METHODS))
    ap.add_argument("--sets", nargs="+", default=["selecao_j30", "selecao_j60"], choices=sorted(ex.SETS))
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--time-j30", type=int, default=10)
    ap.add_argument("--time-j60", type=int, default=30)
    ap.add_argument("--control", type=int, default=0, help="0 = parametros fixos, 1 = Q-Learning")
    ap.add_argument("--budget", type=int, default=0,
                    help="orcamento de cronogramas por execucao (0 = so tempo). Com orcamento, o tempo vira "
                         "apenas um teto de seguranca (--time-cap)")
    ap.add_argument("--time-cap", type=int, default=120, help="teto de tempo (s) quando ha --budget")
    ap.add_argument("--fbi", type=int, choices=[0, 1], default=1,
                    help="1 = decoder com FBI (padrao); 0 = so SSGS, isola o efeito da estrategia de busca")
    a = ap.parse_args()

    exe = build(a.fbi)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if a.budget:
        a.time_j30 = a.time_j60 = a.time_cap
    out = ROOT / "results" / (f"mh_{stamp}" + (f"_b{a.budget}" if a.budget else "") + ("" if a.fbi else "_semFBI"))
    out.mkdir(parents=True, exist_ok=True)

    # arquiva saidas antigas para nao misturar experimentos
    old = [p for p in RES.iterdir() if p.is_file() and p.name != ".gitkeep"]
    if old:
        arch = RES / f"old_{stamp}"
        arch.mkdir(exist_ok=True)
        for p in old:
            shutil.move(str(p), arch / p.name)
        print(f"saidas anteriores movidas para {arch}")

    scen = {}
    worst = 0
    for s in a.sets:
        t = a.time_j60 if "j60" in s else a.time_j30
        path = ROOT / "rko" / "Instances" / "RCPSP" / f"mh-{s}.csv"
        ex.cmd_scenario(argparse.Namespace(instances=[], set=s, time=t, runs=a.runs, out=str(path)))
        scen[s] = path
        worst += len(ex.SETS[s]) * a.runs * t
    worst *= len(a.methods)
    if a.budget:
        print(f"orcamento: {a.budget} cronogramas por execucao (teto de {a.time_cap} s)")
    else:
        print(f"pior caso (sem parada por otimo): {worst / 60:.0f} min", end=" ")
    print(f" — CPU: {cpu_name()}, {os.cpu_count()} threads",
          flush=True)

    (out / "machine.txt").write_text(
        f"data: {datetime.now().isoformat(timespec='seconds')}\nCPU: {cpu_name()}\nthreads logicas: {os.cpu_count()}\n"
        f"sistema: {platform.platform()}\nmetodos: {' '.join(a.methods)}\nconjuntos: {' '.join(a.sets)}\n"
        f"execucoes: {a.runs}\ntempo J30: {a.time_j30} s\ntempo J60: {a.time_j60} s\ncontrole: {a.control}\n"
        f"orcamento: {a.budget if a.budget else 'sem limite (parada por tempo)'} cronogramas por execucao\n"
        f"decoder: chaves -> lista topologica -> SSGS{' + FBI' if a.fbi else ' (sem FBI)'}; parada no otimo conhecido\n")

    t0 = time.time()
    for m in a.methods:
        for s, path in scen.items():
            print(f"[{time.time() - t0:6.0f}s] {m:6s} em {s} ...", flush=True)
            with open(out / f"log_{m}_{s}.txt", "w") as log:
                env = dict(os.environ, RCPSP_MAX_EVALS=str(a.budget))
                subprocess.run([str(exe), f"../Instances/RCPSP/{path.name}", str(METHODS[m]), str(a.control), "0"],
                               cwd=PROG, check=True, stdout=log, stderr=subprocess.STDOUT, env=env)

    for p in RES.iterdir():
        if p.is_file() and p.name != ".gitkeep":
            shutil.copy(p, out / p.name)

    refs = [str(ROOT / "results/reference_j30.csv"), str(ROOT / "results/reference_j60.csv")]
    ex.cmd_summary(argparse.Namespace(ref=refs, stats=[str(out / "Stats_*.csv")], out=str(out / "summary.csv")))
    md = comparison_md(out / "summary.csv", a.methods)
    (out / "comparison.md").write_text(md + "\n")
    print("\n" + md + f"\n\nresultados em {out} (tempo total {(time.time() - t0) / 60:.1f} min)")


if __name__ == "__main__":
    main()
