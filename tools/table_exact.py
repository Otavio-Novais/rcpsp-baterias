"""Tabela da Etapa 5 a partir do CSV de ampl/run_exact.py.

Uso: python3 tools/table_exact.py results/exact_selecao_j30_gurobi_D.csv
     -> imprime a tabela em Markdown e grava <csv>.tex (LaTeX, booktabs)
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import psplib  # noqa: E402

COLS = [  # (chave, cabecalho, alinhamento)
    ("instance", "Instância", "l"),
    ("params", "NC / RF / RS", "c"),
    ("H", "$H$", "r"),
    ("lb_trivial", "LB$_0$", "r"),
    ("lp", "LP", "r"),
    ("cmax", "$C_{\\max}$", "r"),
    ("bound", "Lim. inf.", "r"),
    ("gap_pct", "Gap (\\%)", "r"),
    ("ref", "Ref.", "r"),
    ("status", "Status", "c"),
    ("time_s", "Tempo (s)", "r"),
]


def fmt(v, nd=1):
    if v in ("", None):
        return "--"
    try:
        f = float(v)
    except ValueError:
        return str(v)
    return f"{f:.0f}" if f.is_integer() else f"{f:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--tex")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv)))
    if not rows:
        sys.exit("CSV vazio")

    for r in rows:
        try:
            _, g, _ = psplib.parse_name(r["instance"])
            nc, rf, rs = psplib.progen_params(g)
            r["params"] = f"{nc} / {rf} / {rs}"
        except ValueError:
            r["params"] = ""
        r["status"] = {"OTIMO": "ótimo", "LIMIT": "limite"}.get(r["status"], r["status"].lower())

    n = len(rows)
    n_opt = sum(r["status"] == "ótimo" for r in rows)
    gaps = [float(r["gap_pct"]) for r in rows if r["gap_pct"] not in ("", None)]
    times = [float(r["time_s"]) for r in rows]
    hit = sum(1 for r in rows if r["cmax"] and r["ref"] and int(float(r["cmax"])) == int(float(r["ref"])))
    solver, form = rows[0]["solver"], rows[0]["form"]
    summary = (f"{n_opt}/{n} provadas ótimas; Cmax igual à referência em {hit}/{n}; "
               f"gap médio {sum(gaps) / len(gaps):.2f}%; tempo médio {sum(times) / n:.1f} s "
               f"(solver {solver}, precedência {'desagregada' if form == 'D' else 'agregada'}).")

    # Markdown
    head = [c[1].replace("$", "").replace("\\", "").replace("_{max}", "max").replace("_0", "0") for c in COLS]
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join("---" if c[2] == "l" else "---:" if c[2] == "r" else ":---:" for c in COLS) + "|")
    for r in rows:
        print("| " + " | ".join(fmt(r.get(c[0], ""), 2 if c[0] == "gap_pct" else 1) for c in COLS) + " |")
    print("\n" + summary)

    # LaTeX
    tex = Path(a.tex) if a.tex else Path(a.csv).with_suffix(".tex")
    L = ["% gerado por tools/table_exact.py — requer \\usepackage{booktabs}",
         "\\begin{table}[ht]", "\\centering", "\\small",
         f"\\caption{{Resultados do modelo PLIM tempo-indexado (solver {solver}).}}",
         "\\label{tab:exato}",
         "\\begin{tabular}{" + "".join(c[2] for c in COLS) + "}", "\\toprule",
         " & ".join(c[1] for c in COLS) + " \\\\", "\\midrule"]
    for r in rows:
        cells = [fmt(r.get(c[0], ""), 2 if c[0] == "gap_pct" else 1) for c in COLS]
        L.append(" & ".join(x.replace("_", "\\_") for x in cells) + " \\\\")
    L += ["\\bottomrule", "\\end{tabular}",
          "\\par\\smallskip\\footnotesize " + summary.replace("%", "\\%"),
          "\\par\\footnotesize $H$: horizonte (SSGS com regras de prioridade + FBI); "
          "LB$_0$: limitante trivial (caminho crítico/recurso); LP: relaxação linear; "
          "Lim.~inf.: melhor limitante do solver; Ref.: ótimo de referência.",
          "\\end{table}"]
    tex.write_text("\n".join(L) + "\n")
    print(f"\nLaTeX -> {tex}")


if __name__ == "__main__":
    main()
