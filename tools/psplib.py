"""Leitura de instancias RCPSP da PSPLIB nos formatos .sm (original) e .dzn (MiniZinc).

Representacao comum (somente atividades reais, indices 0..J-1):
    Instance(name, J, K, cap, dur, req, succ)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Instance:
    name: str
    J: int
    K: int
    cap: list[int]
    dur: list[int]
    req: list[list[int]]          # req[j][k]
    succ: list[list[int]]         # sucessoras imediatas (reais)
    pred: list[list[int]] = field(default_factory=list)

    def __post_init__(self):
        if not self.pred:
            self.pred = [[] for _ in range(self.J)]
            for j, ss in enumerate(self.succ):
                for s in ss:
                    self.pred[s].append(j)

    @property
    def horizon(self) -> int:
        return sum(self.dur)

    def topo_order(self) -> list[int]:
        indeg = [len(p) for p in self.pred]
        order = [j for j in range(self.J) if indeg[j] == 0]
        for j in order:
            for s in self.succ[j]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    order.append(s)
        assert len(order) == self.J, "rede com ciclo"
        return order

    def lb_cpm(self) -> int:
        es = [0] * self.J
        for j in self.topo_order():
            for s in self.succ[j]:
                es[s] = max(es[s], es[j] + self.dur[j])
        return max(es[j] + self.dur[j] for j in range(self.J))

    def lb_resource(self) -> int:
        lb = 0
        for k in range(self.K):
            work = sum(self.dur[j] * self.req[j][k] for j in range(self.J))
            lb = max(lb, -(-work // self.cap[k]))
        return lb

    def lower_bound(self) -> int:
        return max(self.lb_cpm(), self.lb_resource())


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", text)]


def read_dzn(path: str | Path) -> Instance:
    txt = Path(path).read_text()

    def block(key: str) -> str:
        m = re.search(rf"(?<![\w]){key}\s*=\s*(.*?);", txt, re.S)
        if not m:
            raise ValueError(f"{key} nao encontrado em {path}")
        return m.group(1)

    K = _ints(block("n_res"))[0]
    J = _ints(block("n_tasks"))[0]
    cap = _ints(block("rc"))
    dur = _ints(block("d"))
    rr = _ints(block("rr"))
    req = [[rr[k * J + j] for k in range(K)] for j in range(J)]
    succ = [[s - 1 for s in _ints(g)] for g in re.findall(r"\{([^}]*)\}", block("suc"))]
    assert len(cap) == K and len(dur) == J and len(succ) == J
    return Instance(Path(path).stem, J, K, cap, dur, req, succ)


def read_sm(path: str | Path) -> Instance:
    lines = Path(path).read_text().splitlines()

    def find(tag: str) -> int:
        return next(i for i, l in enumerate(lines) if tag in l)

    n_jobs = _ints(lines[find("jobs (incl. supersource/sink")].split(":")[1])[0]
    K = _ints(lines[find("- renewable")].split(":")[1])[0]
    J = n_jobs - 2
    succ: list[list[int]] = [[] for _ in range(J)]
    dur = [0] * J
    req = [[0] * K for _ in range(J)]

    i0 = find("PRECEDENCE RELATIONS:") + 2
    for r in range(n_jobs):
        v = _ints(lines[i0 + r])
        job, ns = v[0], v[2]
        if job in (1, n_jobs):
            continue
        succ[job - 2] = [s - 2 for s in v[3:3 + ns] if s != n_jobs]

    i0 = find("REQUESTS/DURATIONS:") + 3
    for r in range(n_jobs):
        v = _ints(lines[i0 + r])
        job = v[0]
        if job in (1, n_jobs):
            continue
        dur[job - 2] = v[2]
        req[job - 2] = v[3:3 + K]

    cap = _ints(lines[find("RESOURCEAVAILABILITIES:") + 2])[:K]
    return Instance(Path(path).stem, J, K, cap, dur, req, succ)


def read(path: str | Path) -> Instance:
    p = Path(path)
    if p.suffix.lower() == ".sm":
        return read_sm(p)
    if p.suffix.lower() == ".dzn":
        return read_dzn(p)
    raise ValueError(f"extensao nao suportada: {p}")


# Parametros do gerador ProGen para os conjuntos J30/J60 (48 grupos x 10 instancias):
# grupo g -> NC (complexidade da rede), RF (fator de recurso), RS (forca do recurso).
# Menor RS = recursos mais escassos; RF = 1 e RS = 0.2 sao os grupos mais dificeis.
NC_LEVELS = (1.5, 1.8, 2.1)
RF_LEVELS = (0.25, 0.5, 0.75, 1.0)
RS_LEVELS = (0.2, 0.5, 0.7, 1.0)


def progen_params(group: int) -> tuple[float, float, float]:
    g = group - 1
    return NC_LEVELS[g // 16], RF_LEVELS[(g % 16) // 4], RS_LEVELS[g % 4]


def parse_name(name: str) -> tuple[str, int, int]:
    """'J30_13_4' ou 'j3013_4' -> ('j30', 13, 4)."""
    m = re.match(r"[Jj](30|60|90|120)_?(\d+)_(\d+)$", Path(name).stem)
    if not m:
        raise ValueError(name)
    size, rest, inst = m.groups()
    return f"j{size}", int(rest), int(inst)


def psplib_name(name: str) -> str:
    """Nome no padrao da PSPLIB: 'J30_13_4' -> 'j3013_4'."""
    size, g, i = parse_name(name)
    return f"{size}{g}_{i}"
