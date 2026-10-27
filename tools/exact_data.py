"""Dados do modelo exato (ampl/rcpsp.mod) a partir de uma instancia PSPLIB.

Numeracao das atividades no modelo (igual a PSPLIB e a Etapa 4):
    1        = atividade ficticia de inicio
    2..n-1   = atividades reais (job numbers da PSPLIB)
    n = J+2  = atividade ficticia de fim (seu inicio e o makespan)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import heuristics as heu
from psplib import Instance


@dataclass
class ExactData:
    inst: Instance
    n: int
    K: list[str]
    p: dict[int, int]
    r: dict[tuple[int, str], int]
    R: dict[str, int]
    P: dict[int, list[int]]
    H: int
    ES: dict[int, int]
    LS: dict[int, int]
    rule: str            # regra de prioridade que gerou H
    lb: int              # lower bound trivial (max CPM, recurso)
    start: dict[int, int] | None = None   # cronograma heuristico (solucao inicial / MIP start)

    @property
    def n_binaries(self) -> int:
        return sum(self.LS[j] - self.ES[j] + 1 for j in range(1, self.n + 1))


def build(inst: Instance, use_fbi: bool = True, horizon: int | None = None) -> ExactData:
    """horizon=None -> H = melhor heuristica SSGS (+FBI); senao usa o valor dado (>= otimo!)."""
    st = None
    if horizon is None:
        H, rule, st = heu.heuristic_upper_bound(inst, use_fbi=use_fbi)
    else:
        H, rule = horizon, "dado"

    n = inst.J + 2
    K = [f"R{k + 1}" for k in range(inst.K)]
    es, q = heu.earliest_starts(inst), heu.tails(inst)
    lb = inst.lower_bound()
    if H < lb:
        raise ValueError(f"H={H} menor que o lower bound {lb}")

    p = {1: 0, n: 0}
    ES = {1: 0, n: lb}
    LS = {1: 0, n: H}
    P: dict[int, list[int]] = {1: [], n: []}
    r: dict[tuple[int, str], int] = {}
    for j in range(inst.J):
        a = j + 2
        p[a] = inst.dur[j]
        ES[a] = es[j]
        LS[a] = H - q[j]
        P[a] = [i + 2 for i in inst.pred[j]] or [1]
        for k in range(inst.K):
            if inst.req[j][k] > 0:
                r[(a, K[k])] = inst.req[j][k]
        if not inst.succ[j]:
            P[n].append(a)
    R = {K[k]: inst.cap[k] for k in range(inst.K)}
    start = None
    if st is not None:
        start = {1: 0, n: heu.makespan(inst, st)}
        start.update({j + 2: st[j] for j in range(inst.J)})
        assert all(ES[j] <= start[j] <= LS[j] for j in start), "solucao heuristica fora das janelas"
    return ExactData(inst, n, K, p, r, R, P, H, ES, LS, rule, lb, start)


def write_dat(d: ExactData, path: str | Path) -> None:
    L = [f"# {d.inst.name}: H={d.H} ({d.rule}), LB trivial={d.lb}",
         f"param n := {d.n};",
         "set K := " + " ".join(d.K) + ";",
         f"param H := {d.H};",
         "param p := " + " ".join(f"{j} {d.p[j]}" for j in range(1, d.n + 1)) + ";",
         "param R := " + " ".join(f"{k} {d.R[k]}" for k in d.K) + ";",
         "param r :=\n" + "\n".join(f"  {j} {k} {v}" for (j, k), v in sorted(d.r.items())) + ";",
         "param ES := " + " ".join(f"{j} {d.ES[j]}" for j in range(1, d.n + 1)) + ";",
         "param LS := " + " ".join(f"{j} {d.LS[j]}" for j in range(1, d.n + 1)) + ";"]
    for j in range(1, d.n + 1):
        if d.P[j]:
            L.append(f"set P[{j}] := " + " ".join(map(str, sorted(d.P[j]))) + ";")
    if d.start:
        # valor inicial de x = cronograma heuristico (usado como MIP start pelo solver)
        L.append("var x :=\n" + "\n".join(f"  {j} {t} 1" for j, t in sorted(d.start.items())) + ";")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n")


def starts_from_x(d: ExactData, x: dict[tuple[int, int], float]) -> list[int | None]:
    """Instantes de inicio das atividades REAIS (indice 0..J-1) a partir de x[j,t]."""
    st: list[int | None] = [None] * d.inst.J
    for (j, t), v in x.items():
        if v > 0.5 and 2 <= j <= d.n - 1:
            st[j - 2] = t
    return st


def verify(d: ExactData, x: dict[tuple[int, int], float], cmax: float) -> tuple[bool, str]:
    """Confere a solucao do solver de forma independente do modelo."""
    if sum(1 for v in x.values() if v > 0.5) == 0:
        return False, "sem solucao inteira"
    starts = [sum(1 for (jj, _), v in x.items() if jj == j and v > 0.5) for j in range(1, d.n + 1)]
    if any(c != 1 for c in starts):
        return False, "alguma atividade nao comeca exatamente uma vez"
    st = starts_from_x(d, x)
    if not heu.check_schedule(d.inst, st):
        return False, "cronograma viola precedencia ou recurso"
    real = heu.makespan(d.inst, st)
    if real > round(cmax):
        return False, f"makespan real {real} maior que o objetivo {cmax}"
    return True, "ok"
