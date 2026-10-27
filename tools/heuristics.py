"""SSGS com regras de prioridade, FBI, janelas de tempo (CPM) e verificador.

Usado pelo metodo exato para definir o horizonte H (limitante superior valido)
e as janelas [ES_j, LS_j] das variaveis x_jt, como descrito na Etapa 4.
"""
from __future__ import annotations

import heapq

from psplib import Instance


# ----------------------------------------------------------------------------
# SSGS
# ----------------------------------------------------------------------------
def ssgs(inst: Instance, order: list[int], preds: list[list[int]] | None = None) -> list[int]:
    """Serial Schedule Generation Scheme. `order` deve respeitar a rede `preds`."""
    preds = inst.pred if preds is None else preds
    H = inst.horizon + 1
    use = [[0] * inst.K for _ in range(H)]
    st = [-1] * inst.J
    for j in order:
        t = max((st[i] + inst.dur[i] for i in preds[j]), default=0)
        while True:
            conflict = next((tau for tau in range(t, t + inst.dur[j])
                             if any(use[tau][k] + inst.req[j][k] > inst.cap[k] for k in range(inst.K))), None)
            if conflict is None:
                break
            t = conflict + 1
        st[j] = t
        for tau in range(t, t + inst.dur[j]):
            for k in range(inst.K):
                use[tau][k] += inst.req[j][k]
    return st


def makespan(inst: Instance, st: list[int]) -> int:
    return max(st[j] + inst.dur[j] for j in range(inst.J))


def priority_list(inst: Instance, prio: list[float]) -> list[int]:
    """Lista topologica: a cada passo, a elegivel de MENOR prioridade (desempate pelo indice)."""
    indeg = [len(p) for p in inst.pred]
    heap = [(prio[j], j) for j in range(inst.J) if indeg[j] == 0]
    heapq.heapify(heap)
    out = []
    while heap:
        _, j = heapq.heappop(heap)
        out.append(j)
        for s in inst.succ[j]:
            indeg[s] -= 1
            if indeg[s] == 0:
                heapq.heappush(heap, (prio[s], s))
    return out


# ----------------------------------------------------------------------------
# CPM
# ----------------------------------------------------------------------------
def earliest_starts(inst: Instance) -> list[int]:
    es = [0] * inst.J
    for j in inst.topo_order():
        for s in inst.succ[j]:
            es[s] = max(es[s], es[j] + inst.dur[j])
    return es


def tails(inst: Instance) -> list[int]:
    """tail_j = caminho mais longo do inicio de j ate o fim do projeto (inclui p_j)."""
    q = [0] * inst.J
    for j in reversed(inst.topo_order()):
        q[j] = inst.dur[j] + max((q[s] for s in inst.succ[j]), default=0)
    return q


# ----------------------------------------------------------------------------
# Regras de prioridade classicas (Kolisch, 1996) -- menor valor = maior prioridade
# ----------------------------------------------------------------------------
def all_successors(inst: Instance) -> list[set[int]]:
    tot: list[set[int]] = [set() for _ in range(inst.J)]
    for j in reversed(inst.topo_order()):
        for s in inst.succ[j]:
            tot[j].add(s)
            tot[j] |= tot[s]
    return tot


def priority_rules(inst: Instance) -> dict[str, list[float]]:
    es = earliest_starts(inst)
    q = tails(inst)
    T = max(es[j] + inst.dur[j] for j in range(inst.J))           # caminho critico
    lf = [T - q[j] + inst.dur[j] for j in range(inst.J)]           # latest finish (CPM)
    ls = [T - q[j] for j in range(inst.J)]                         # latest start
    tot = all_successors(inst)
    return {
        "LFT": [lf[j] for j in range(inst.J)],                     # menor latest finish
        "LST": [ls[j] for j in range(inst.J)],                     # menor latest start
        "MSLK": [ls[j] - es[j] for j in range(inst.J)],            # menor folga
        "MTS": [-len(tot[j]) for j in range(inst.J)],              # mais sucessoras (total)
        "GRPW": [-(inst.dur[j] + sum(inst.dur[s] for s in inst.succ[j])) for j in range(inst.J)],
        "LPT": [-inst.dur[j] for j in range(inst.J)],              # maior duracao
        "MIS": [-len(inst.succ[j]) for j in range(inst.J)],        # mais sucessoras imediatas
    }


# ----------------------------------------------------------------------------
# FBI (justificacao dupla; Valls et al., 2005)
# ----------------------------------------------------------------------------
def fbi(inst: Instance, st: list[int], max_it: int = 5) -> list[int]:
    rank = {j: h for h, j in enumerate(inst.topo_order())}
    best, cbest = st[:], makespan(inst, st)
    for _ in range(max_it):
        order = sorted(range(inst.J), key=lambda j: (-(best[j] + inst.dur[j]), -rank[j]))
        sb = ssgs(inst, order, inst.succ)                           # rede invertida
        cb = makespan(inst, sb)
        back = [cb - (sb[j] + inst.dur[j]) for j in range(inst.J)]
        order = sorted(range(inst.J), key=lambda j: (back[j], rank[j]))
        sf = ssgs(inst, order)
        cf = makespan(inst, sf)
        if cf < cbest:
            best, cbest = sf, cf
        else:
            break
    return best


def heuristic_upper_bound(inst: Instance, use_fbi: bool = True) -> tuple[int, str, list[int]]:
    """Melhor makespan entre as regras de prioridade (+ FBI). Retorna (H, regra, inicios)."""
    best = None
    for name, prio in priority_rules(inst).items():
        st = ssgs(inst, priority_list(inst, prio))
        label = name
        if use_fbi:
            st2 = fbi(inst, st)
            if makespan(inst, st2) < makespan(inst, st):
                st, label = st2, name + "+FBI"
        c = makespan(inst, st)
        if best is None or c < best[0]:
            best = (c, label, st)
    assert best is not None and check_schedule(inst, best[2])
    return best


# ----------------------------------------------------------------------------
# Verificador independente
# ----------------------------------------------------------------------------
def check_schedule(inst: Instance, st: list[int]) -> bool:
    if len(st) != inst.J or any(s is None or s < 0 for s in st):
        return False
    for j in range(inst.J):
        for s in inst.succ[j]:
            if st[j] + inst.dur[j] > st[s]:
                return False
    for t in range(makespan(inst, st)):
        for k in range(inst.K):
            if sum(inst.req[j][k] for j in range(inst.J) if st[j] <= t < st[j] + inst.dur[j]) > inst.cap[k]:
                return False
    return True
