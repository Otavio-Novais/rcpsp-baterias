"""Gera as figuras dos resultados (Etapas 5 e 6) a partir dos CSVs em results/.

Uso (raiz do repositorio): python3 graficos/gera_graficos.py

Grava graficos/fig*.pdf (para o LaTeX) e graficos/fig*.png (300 dpi) e imprime os valores
plotados, para conferir com as Tabelas 1 e 2 de relatorios/etapa6/etapa6.tex.
"""
import csv
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import psplib  # noqa: E402
from stats_mh import METHODS, load, load_ref  # noqa: E402

EXATO = ["results/exact_selecao_j30_gurobi_D.csv", "results/exact_selecao_j60_gurobi_D.csv"]
MH = {  # (criterio de parada, decodificador) -> diretorio da rodada
    ("tempo", "fbi"): "results/mh_20261102_2306",
    ("tempo", "ssgs"): "results/mh_20261103_0018_semFBI",
    ("orc", "fbi"): "results/mh_20261103_0825_b50000",
    ("orc", "ssgs"): "results/mh_20261103_0828_b50000_semFBI",
}
CRIT = {"tempo": "Tempo (10 s / 30 s)", "orc": "50.000 cronogramas"}
DEC = {"fbi": "SSGS + FBI", "ssgs": "Só SSGS"}

# cor fixa por entidade (3 primeiras posicoes da paleta de referencia do dataviz; Gurobi neutro)
COR = {"RKO": "#2a78d6", "GA": "#eb6834", "BRKGA": "#1baf7a", "Gurobi": "#52514e"}
TINTA, TINTA2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
LARGURA = 6.3  # polegadas, ~16 cm (largura de texto dos relatorios)

plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "text.color": TINTA, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.edgecolor": "#b5b4ae", "axes.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.facecolor": FUNDO, "axes.facecolor": FUNDO,
    "legend.frameon": False, "pdf.fonttype": 42, "lines.linewidth": 1.5,
})


def virgula(fmt="{:g}"):
    return FuncFormatter(lambda v, _: fmt.format(v).replace(".", ","))


def br(v, d=2):
    return f"{v:.{d}f}".replace(".", ",")


def salva(fig, nome):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{nome}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> graficos/{nome}.pdf / .png")


def rpd(c, ref):
    return 100 * (c - ref) / ref


# ---------------------------------------------------------------- dados
ex = []  # ordem da Tabela 1
for f in EXATO:
    for r in csv.DictReader(open(ROOT / f)):
        ref = int(r["ref"])
        ex.append({"inst": r["file"].split("/")[-1], "nome": psplib.psplib_name(r["file"].split("/")[-1]),
                   "grupo": "J30" if r["J"] == "30" else "J60", "ref": ref, "cmax": int(r["cmax"]),
                   "bound": float(r["bound"]), "lp": float(r["lp"]), "t": float(r["time_s"]),
                   "otimo": r["status"] == "OTIMO", "gap": float(r["gap_pct"])})
REF = load_ref()
R = {k: load(ROOT / d, REF) for k, d in MH.items()}
GRUPOS = ("J30", "J60")


def rko(k, inst):
    v = [x["rpd"] for x in R[k][(inst, "RKO")]]
    return min(v), st.mean(v), max(v), st.mean(x["tt"] for x in R[k][(inst, "RKO")])


def paineis_por_instancia():
    n = {g: sum(e["grupo"] == g for e in ex) for g in GRUPOS}
    fig, axs = plt.subplots(2, 1, figsize=(LARGURA, 0.36 * sum(n.values()) + 1.6),
                            gridspec_kw={"height_ratios": [n[g] for g in GRUPOS]}, layout="constrained")
    for ax, g in zip(axs, GRUPOS):
        E = [e for e in ex if e["grupo"] == g]
        ax.set_yticks(range(len(E)), [e["nome"] for e in E])
        ax.set_ylim(len(E) - 0.5, -0.5)
        ax.grid(axis="y", visible=False)
        ax.set_title(g, loc="left", fontweight="bold", color=TINTA)
        ax.axvline(0, color=TINTA2, lw=0.9, zorder=1)
    return fig, axs, n


# ---------------------------------------------------------------- figura 1
def fig1():
    print("\nFigura 1 - Exato x RKO por instancia (RPD %): Gurobi | RKO tempo medio | RKO 50k medio")
    fig, axs, _ = paineis_por_instancia()
    for ax, g in zip(axs, GRUPOS):
        E = [e for e in ex if e["grupo"] == g]
        for y, e in enumerate(E):
            gu = rpd(e["cmax"], e["ref"])
            ax.plot(gu, y - 0.24, "D", ms=6, color=COR["Gurobi"], mfc=COR["Gurobi"] if e["otimo"] else FUNDO,
                    mew=1.4, zorder=3)
            for dy, k, cheio in ((0, ("tempo", "fbi"), True), (0.24, ("orc", "fbi"), False)):
                lo, m, hi, _ = rko(k, e["inst"])
                ax.plot([lo, hi], [y + dy] * 2, color=COR["RKO"], lw=1.2, solid_capstyle="round", zorder=2)
                ax.plot(m, y + dy, "o", ms=6, color=COR["RKO"], mfc=COR["RKO"] if cheio else FUNDO, mew=1.4,
                        zorder=3)
            print(f"  {e['nome']:9s} {br(gu):>6s} {br(rko(('tempo', 'fbi'), e['inst'])[1]):>6s} "
                  f"{br(rko(('orc', 'fbi'), e['inst'])[1]):>6s}")
        ax.set_xlim(left=-0.4)
        ax.xaxis.set_major_formatter(virgula())
    axs[-1].set_xlabel("RPD em relação ao ótimo C* (%)  —  0 = ótimo\n"
                       "RKO: ponto = média das 10 execuções; traço = melhor a pior execução")
    h = [Line2D([], [], ls="", marker="D", ms=6, color=COR["Gurobi"], mew=1.4, label="Gurobi 600 s, ótimo provado"),
         Line2D([], [], ls="", marker="D", ms=6, color=COR["Gurobi"], mfc=FUNDO, mew=1.4,
                label="Gurobi 600 s, limite de tempo"),
         Line2D([], [], marker="o", ms=6, color=COR["RKO"], lw=1.2, label="RKO, tempo (10 s / 30 s)"),
         Line2D([], [], marker="o", ms=6, color=COR["RKO"], mfc=FUNDO, mew=1.4, lw=1.2,
                label="RKO, 50.000 cronogramas")]
    fig.legend(handles=h, loc="outside upper center", ncol=2)
    salva(fig, "fig1_exato_rko")


# ---------------------------------------------------------------- figura 2
def fig2():
    print("\nFigura 2 - Qualidade x tempo (RPD medio %, tempo medio s)")
    fig, ax = plt.subplots(figsize=(LARGURA, 3.4))
    forma = {"J30": "o", "J60": "s"}
    for g in GRUPOS:
        E = [e for e in ex if e["grupo"] == g]
        pts = [("Gurobi", "Gurobi 600 s", st.mean(e["t"] for e in E),
                st.mean(rpd(e["cmax"], e["ref"]) for e in E), COR["Gurobi"], True)]
        for k, rot, cheio in ((("tempo", "fbi"), "RKO, tempo", True), (("orc", "fbi"), "RKO, 50.000 cron.", False)):
            pts.append(("RKO", rot, st.mean(rko(k, e["inst"])[3] for e in E),
                        st.mean(rko(k, e["inst"])[1] for e in E), COR["RKO"], cheio))
        for _, rot, t, q, c, cheio in pts:
            ax.plot(t, q, forma[g], ms=8, color=c, mfc=c if cheio else FUNDO, mew=1.6, zorder=3)
            ax.annotate(f"{rot} ({g})\n{br(q)}% em {br(t, 1 if t >= 1 else 2)} s", (t, q), xytext=(9, 0),
                        textcoords="offset points", va="center", fontsize=7.5, color=TINTA)
            print(f"  {g} {rot:18s} RPD {br(q):>5s}%  tempo {br(t):>7s} s")
    ax.set_xscale("log")
    ax.set_xlim(0.08, 4000)
    ax.set_ylim(-0.3, 6.2)
    ax.xaxis.set_major_formatter(virgula())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(virgula())
    ax.set_xlabel("Tempo médio por execução (s, escala log)")
    ax.set_ylabel("RPD médio (%)")
    h = [Line2D([], [], ls="", marker=forma[g], ms=7, color=TINTA2, mfc=FUNDO, mew=1.4, label=g) for g in GRUPOS]
    h += [Line2D([], [], ls="", marker="o", ms=7, color=COR["Gurobi"], label="Gurobi"),
          Line2D([], [], ls="", marker="o", ms=7, color=COR["RKO"], label="RKO, tempo"),
          Line2D([], [], ls="", marker="o", ms=7, color=COR["RKO"], mfc=FUNDO, mew=1.4, label="RKO, 50.000 cron.")]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=5)
    salva(fig, "fig2_qualidade_tempo")


# ---------------------------------------------------------------- figura 3
def fig3():
    print("\nFigura 3 - RPD medio (%) nas 15 instancias: GA BRKGA RKO | Friedman p")
    insts = [e["inst"] for e in ex]
    fig, axs = plt.subplots(1, 2, figsize=(LARGURA, 3.3), layout="constrained")
    w = 0.26
    for ax, crit in zip(axs, CRIT):
        topo, ticks = 0, []
        for gx, dec in enumerate(DEC):
            D = R[(crit, dec)]
            med = {m: [st.mean(x["rpd"] for x in D[(i, m)]) for i in insts] for m in METHODS}
            p = stats.friedmanchisquare(*med.values()).pvalue
            for j, m in enumerate(METHODS):
                x = gx + (j - 1) * w
                v = st.mean(med[m])
                ax.bar(x, v, w, color=COR[m], edgecolor=FUNDO, linewidth=1.5, zorder=2)
                jit = [(k % 5 - 2) * w / 9 for k in range(len(insts))]
                ax.scatter([x + d for d in jit], med[m], s=9, facecolor=FUNDO, edgecolor=TINTA2, lw=0.7,
                           zorder=3, alpha=0.9)
                ax.text(x, v, br(v), ha="center", va="bottom", fontsize=7.5, color=TINTA, zorder=4,
                        bbox={"boxstyle": "round,pad=0.15", "fc": FUNDO, "ec": "none", "alpha": 0.85})
                topo = max(topo, max(med[m]))
            ticks.append(f"{DEC[dec]}\nFriedman p = {br(p, 3)}")
            print(f"  {CRIT[crit]:20s} {DEC[dec]:10s} " + " ".join(br(st.mean(med[m])) for m in METHODS)
                  + f" | {br(p, 3)}")
        ax.set_xticks(range(len(DEC)), ticks)
        ax.set_xlim(-0.55, 1.55)
        ax.set_ylim(0, topo * 1.08)
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(virgula())
        ax.set_title(CRIT[crit], color=TINTA, fontweight="bold")
    axs[0].set_ylabel("RPD médio (%)")
    h = [plt.Rectangle((0, 0), 1, 1, color=COR[m], label=m) for m in METHODS]
    h.append(Line2D([], [], ls="", marker="o", ms=4, color=TINTA2, mfc=FUNDO, label="média de cada instância"))
    fig.legend(handles=h, loc="outside upper center", ncol=4)
    salva(fig, "fig3_estrategias_busca")


# ---------------------------------------------------------------- figura 4
def fig4():
    print("\nFigura 4 - Gap do Gurobi (% relativo a C*): LP | limitante | cmax | gap")
    fig, axs, _ = paineis_por_instancia()
    c = COR["Gurobi"]
    for ax, g in zip(axs, GRUPOS):
        E = [e for e in ex if e["grupo"] == g]
        for y, e in enumerate(E):
            lp, lb, ub = (rpd(e[k], e["ref"]) for k in ("lp", "bound", "cmax"))
            ax.plot([lb, ub], [y, y], color="#c3c2b7", lw=5, solid_capstyle="butt", zorder=2)
            ax.plot(lp, y, "o", ms=5, color=c, mfc=FUNDO, mew=1.2, zorder=3)
            ax.plot(lb, y, "|", ms=10, color=c, mew=1.8, zorder=3)
            ax.plot(ub, y, "D", ms=6, color=c, mfc=c if e["otimo"] else FUNDO, mew=1.4, zorder=4)
            txt = f"ótimo em {br(e['t'], 1)} s" if e["otimo"] else f"gap {br(e['gap'], 1)}%"
            ax.annotate(txt, (1.0, y), xycoords=("axes fraction", "data"), xytext=(4, 0),
                        textcoords="offset points", va="center", fontsize=7.5, color=TINTA2)
            print(f"  {e['nome']:9s} LP {br(lp):>6s}  LB {br(lb):>6s}  Cmax {br(ub):>6s}  {txt}")
        ax.xaxis.set_major_formatter(virgula())
    lo = min(rpd(e["lp"], e["ref"]) for e in ex)
    hi = max(rpd(e["cmax"], e["ref"]) for e in ex)
    for ax in axs:
        ax.set_xlim(lo - 2, hi + 2)
    axs[-1].set_xlabel("Desvio em relação ao ótimo C* (%)  —  0 = ótimo")
    h = [Line2D([], [], ls="", marker="o", ms=5, color=c, mfc=FUNDO, mew=1.2, label="relaxação linear (LP)"),
         Line2D([], [], ls="", marker="|", ms=10, color=c, mew=1.8, label="limitante inferior (600 s)"),
         Line2D([], [], ls="", marker="D", ms=6, color=c, mew=1.4, label="Cmax, ótimo provado"),
         Line2D([], [], ls="", marker="D", ms=6, color=c, mfc=FUNDO, mew=1.4, label="Cmax, limite de tempo"),
         Line2D([], [], color="#c3c2b7", lw=5, label="intervalo em aberto")]
    fig.legend(handles=h, loc="outside upper center", ncol=3)
    salva(fig, "fig4_gap_gurobi")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
