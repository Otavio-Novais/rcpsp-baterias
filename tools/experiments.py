"""Utilitarios de experimento para o RKO no RCPSP.

Subcomandos:
  targets   gera rko/Instances/RCPSP/targets.txt (alvos de parada = otimos provados)
  scenario  gera o CSV de cenario lido pelo RKO (instancia, tempo, execucoes)
  summary   junta rko/Results/Stats_*.csv com a referencia e calcula RPD

Exemplos (a partir da raiz do repositorio):
  python3 tools/experiments.py targets results/reference_j30.csv results/reference_j60.csv
  python3 tools/experiments.py scenario --set selecao_j30 --time 10 --runs 10 \
      --out rko/Instances/RCPSP/exp-j30.csv
  python3 tools/experiments.py summary --ref results/reference_j30.csv results/reference_j60.csv \
      --stats rko/Results/Stats_*.csv --out results/summary.csv
"""
from __future__ import annotations

import argparse
import csv
import glob
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import psplib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INST_DIR = ROOT / "rko" / "Instances" / "RCPSP"

# Conjuntos de instancias pre-definidos (nomes dos arquivos .dzn / .sm).
# selecao_j30: a instancia de exemplo da Etapa 3 (j301_1) + 9 instancias
# dos grupos mais dificeis do J30 (recurso escasso, RS = 0.2 e RS = 0.5),
# uma por grupo: a de maior tempo de prova de otimalidade no CP-SAT entre
# as com otimo provado (ver results/reference_j30.csv). Nos grupos com
# RS >= 0.7 o otimo quase sempre coincide com o lower bound, sem contraste.
SETS = {
    "selecao_j30": [
        "j30/J30_1_1.dzn",    # j301_1   exemplo da Etapa 3      NC1.5 RF0.25 RS0.2
        "j30/J30_9_2.dzn",    # j309_2                           NC1.5 RF0.75 RS0.2
        "j30/J30_13_1.dzn",   # j3013_1                          NC1.5 RF1.00 RS0.2
        "j30/J30_25_4.dzn",   # j3025_4                          NC1.8 RF0.75 RS0.2
        "j30/J30_29_8.dzn",   # j3029_8                          NC1.8 RF1.00 RS0.2
        "j30/J30_37_7.dzn",   # j3037_7                          NC2.1 RF0.50 RS0.2
        "j30/J30_41_10.dzn",  # j3041_10                         NC2.1 RF0.75 RS0.2
        "j30/J30_45_6.dzn",   # j3045_6                          NC2.1 RF1.00 RS0.2
        "j30/J30_14_2.dzn",   # j3014_2                          NC1.5 RF1.00 RS0.5
        "j30/J30_30_2.dzn",   # j3030_2                          NC1.8 RF1.00 RS0.5
    ],
}


def read_reference(paths: list[str]) -> dict[str, dict]:
    ref = {}
    for p in paths:
        with open(p) as f:
            for row in csv.DictReader(f):
                ref[row["instance"]] = row
                ref[row["psplib_name"]] = row
    return ref


def cmd_targets(a):
    ref = read_reference(a.reference)
    out = INST_DIR / "targets.txt"
    seen = set()
    n = 0
    with open(out, "w") as f:
        f.write("# alvo de parada por instancia = otimo provado (CP-SAT); gerado por tools/experiments.py\n")
        for row in ref.values():
            if row["instance"] in seen or row["status"] != "OPTIMAL":
                continue
            seen.add(row["instance"])
            size = psplib.parse_name(row["instance"])[0]
            f.write(f"RCPSP/{size}/{row['instance']} {row['ub']}\n")
            n += 1
        # a instancia .sm de exemplo tem o mesmo otimo da J30_1_1
        if "J30_1_1.dzn" in ref and ref["J30_1_1.dzn"]["status"] == "OPTIMAL":
            f.write(f"RCPSP/j30/j301_1.sm {ref['J30_1_1.dzn']['ub']}\n")
    print(f"{n} alvos escritos em {out}")


def cmd_scenario(a):
    insts = list(a.instances)
    if a.set:
        insts += SETS[a.set]
    if not insts:
        sys.exit("informe --set ou instancias")
    for i in insts:
        if not (INST_DIR / i).exists():
            sys.exit(f"instancia nao encontrada: {INST_DIR / i}")
    lines = ["Instance\tTime\t#Runs"] + [f"RCPSP/{i}\t{a.time}\t{a.runs}" for i in insts]
    # SEM quebra de linha no final: o laco while(!feof()) do main.cpp do RKO
    # executaria a ultima instancia duas vezes.
    with open(a.out, "w") as f:
        f.write("\n".join(lines))
    print(f"{len(insts)} instancias -> {a.out}")


def check_consistency(stats_files, runs):
    """Confere o que o RKO reporta (Results_<MH>.csv e Solutions_<MH>.txt) com o
    que o decoder registrou (Stats_<MH>.csv). Divergencia = chaves e makespan
    desencontrados em alguma solucao armazenada -> resultado nao confiavel."""
    import math
    import re
    problems = 0
    checked = 0
    for sp in stats_files:
        d = Path(sp).parent
        mh = Path(sp).stem.removeprefix("Stats_")
        sol_cmax = {}
        sol = d / f"Solutions_{mh}.txt"
        if sol.exists():
            for m in re.finditer(r"Instance: (\S+).*?Cmax=(\d+).*?(INFACTIVEL|FACTIVEL)",
                                 sol.read_text(), re.S):
                sol_cmax[m.group(1)] = int(m.group(2))
                if m.group(3) == "INFACTIVEL":
                    problems += 1
                    print(f"INCONSISTENTE: {m.group(1)} {mh}: solucao final INFACTIVEL")
        res = d / f"Results_{mh}.csv"
        if not res.exists():
            continue
        for line in res.read_text().splitlines():
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            inst, nr = parts[0], int(parts[2])
            reported = [math.floor(float(x) + 1e-9) for x in parts[3:3 + nr]]
            logged = [int(x["cmax"]) for x in runs.get((inst, mh), [])][-nr:]
            if not logged:
                continue
            checked += 1
            if reported != logged:
                problems += 1
                print(f"INCONSISTENTE: {inst} {mh}: RKO reporta {reported}, decoder registrou {logged}")
            if inst in sol_cmax and sol_cmax[inst] != min(reported):
                problems += 1
                print(f"INCONSISTENTE: {inst} {mh}: melhor reportado {min(reported)}, "
                      f"mas a solucao salva decodifica para {sol_cmax[inst]}")
    if checked or problems:
        print(f"checagem de consistencia: {checked} instancia(s) x metodo, {problems} problema(s)")


def cmd_summary(a):
    ref = read_reference(a.ref)
    files = sorted({p for pat in a.stats for p in glob.glob(pat)})
    runs = defaultdict(list)
    for p in files:
        with open(p) as f:
            for row in csv.DictReader(f):
                runs[(row["instance"], row["mh"])].append(row)

    rows = []
    for (inst, mh), rs in sorted(runs.items()):
        name = Path(inst).name
        r = ref.get(name)
        best_ref = int(r["ub"]) if r and r["ub"] not in ("", "None") else None
        cm = [int(x["cmax"]) for x in rs]
        sched = [int(x["schedules_to_best"]) for x in rs]
        ttb = [float(x["time_to_best"]) for x in rs]
        cbest, cmean = min(cm), st.mean(cm)
        rpd = (lambda c: 100.0 * (c - best_ref) / best_ref) if best_ref else (lambda c: float("nan"))
        rows.append({
            "instance": name, "mh": mh, "runs": len(cm), "ref": best_ref,
            "ref_status": r["status"] if r else "", "cmax_best": cbest, "cmax_mean": round(cmean, 2),
            "cmax_sd": round(st.stdev(cm), 2) if len(cm) > 1 else 0.0,
            "rpd_best": round(rpd(cbest), 2), "rpd_mean": round(rpd(cmean), 2),
            "hits": sum(c == best_ref for c in cm) if best_ref else "",
            "schedules_to_best_mean": round(st.mean(sched)),
            "time_to_best_mean": round(st.mean(ttb), 3),
        })
        if best_ref and cbest < best_ref and r["status"] == "OPTIMAL":
            print(f"ATENCAO: {name} {mh} abaixo do otimo ({cbest} < {best_ref}) -> erro no decoder!")

    if not rows:
        sys.exit("nenhuma estatistica encontrada")
    check_consistency(files, runs)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} linhas -> {a.out}")
    for row in rows:
        print(f"{row['instance']:14s} {row['mh']:8s} ref={row['ref']} best={row['cmax_best']} "
              f"mean={row['cmax_mean']} RPDmed={row['rpd_mean']}% hits={row['hits']}/{row['runs']} "
              f"sched_to_best={row['schedules_to_best_mean']} t_best={row['time_to_best_mean']}s")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)

    t = sp.add_parser("targets")
    t.add_argument("reference", nargs="+")
    t.set_defaults(fn=cmd_targets)

    s = sp.add_parser("scenario")
    s.add_argument("instances", nargs="*", help="caminhos relativos a rko/Instances/RCPSP, ex. j30/J30_13_1.dzn")
    s.add_argument("--set", choices=sorted(SETS))
    s.add_argument("--time", type=int, default=10)
    s.add_argument("--runs", type=int, default=10)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_scenario)

    m = sp.add_parser("summary")
    m.add_argument("--ref", nargs="+", required=True)
    m.add_argument("--stats", nargs="+", required=True)
    m.add_argument("--out", required=True)
    m.set_defaults(fn=cmd_summary)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
