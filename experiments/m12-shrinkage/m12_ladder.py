"""M12 — the windowed conservation ladder.

Everything M12 measures rests on one identity.  For a window of frames
``0 .. W`` and any span ``s`` that divides ``W``::

    T_W(s) = sum_{k = 0, s, ..., W-s} log |a_{k, k+s}|

estimates the total log-magnification from frame 0 to frame ``W``.  Every span
estimates the *same* physical quantity, so for an unbiased estimator every row
of the ladder is equal, and equal to the directly measured anchor
``A_W = log |a_{0,W}|``.

This is a strengthened form of M10's ladder.  M10 telescoped to whatever
coverage each span happened to reach and rescaled by ``(n-1)/cov``, which mixes
an extrapolation error into the comparison.  Here every span covers the
identical frame range with the identical endpoints, so the only thing that
varies between rows is the baseline of the individual edges.

**Disjointness.**  ``A_W`` is the single edge ``(0, W)``; ``T_W(s)`` for
``s < W`` contains only span-``s`` edges.  They share no measurement.  The row
``s = W`` is excluded from every ruling because there ``T_W(W) == A_W``
identically — SYNTHESIS §5 item 20.

See ``PREREGISTRATION.md`` §1 for the registered definitions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from m12_lib import RHO, Edge, read_edges

__all__ = [
    "RHO",
    "Ladder",
    "Stack",
    "divisor_spans",
    "ladder",
    "load_stack",
]


def divisor_spans(w: int, available: set[int]) -> list[int]:
    """Spans that divide ``w`` exactly *and* were actually measured.

    A span that was not measured cannot be telescoped: M10's `p4-conservation`
    output has rows with ``links=1`` for spans 3, 6, 12 and 24 because those
    spans were never in the edge set and only the ``--direct0`` pair survived.
    Those rows are meaningless and this function is what stops them existing.
    """
    return [s for s in sorted(available) if s < w and w % s == 0]


@dataclass
class Stack:
    name: str
    n: int
    emap: dict[tuple[int, int], Edge]
    spans: set[int]

    def edge(self, i: int, j: int) -> Edge | None:
        return self.emap.get((i, j))


def load_stack(name: str, path: str, n: int, cfg: str = "m10") -> Stack:
    emap: dict[tuple[int, int], Edge] = {}
    spans: set[int] = set()
    for e in read_edges(path, cfg=cfg):
        if not e.ok:
            continue
        key = (e.i, e.j)
        prev = emap.get(key)
        if prev is None or e.used > prev.used:
            emap[key] = e
        spans.add(e.span)
    return Stack(name=name, n=n, emap=emap, spans=spans)


@dataclass
class Ladder:
    stack: str
    start: int
    w: int
    anchor: float           # A_W = log|a_(start, start+W)|
    anchor_used: int
    anchor_rms: float
    spans: list[int]
    total: dict[int, float]        # s -> T_W(s)
    frac: dict[int, float]         # s -> S_W(s) = T_W(s) / A_W
    links: dict[int, int]
    used_med: dict[int, float]
    rms_med: dict[int, float]

    @property
    def rate_true(self) -> float:
        """Per-frame log-magnification implied by the anchor."""
        return self.anchor / self.w

    def disp_true(self, s: int) -> float:
        """The *true* differential corner displacement of a span-``s`` edge, in
        plane px: ``rho * s * |rate_true|``.  This is fact 45's variable, and it
        is derived from the anchor — a long edge — never from the short edges
        whose bias is under test."""
        return RHO * abs(self.rate_true) * s


def ladder(st: Stack, start: int, w: int, spans: list[int] | None = None) -> Ladder | None:
    """The windowed conservation ladder over frames ``start .. start+w``."""
    anchor_e = st.edge(start, start + w)
    if anchor_e is None:
        return None
    anchor = math.log(abs(anchor_e.a))
    use = divisor_spans(w, st.spans) if spans is None else [s for s in spans if w % s == 0]

    total: dict[int, float] = {}
    frac: dict[int, float] = {}
    links: dict[int, int] = {}
    used_med: dict[int, float] = {}
    rms_med: dict[int, float] = {}
    kept: list[int] = []
    for s in use:
        es = [st.edge(k, k + s) for k in range(start, start + w, s)]
        if any(e is None for e in es):
            continue
        t = float(sum(math.log(abs(e.a)) for e in es))
        total[s] = t
        frac[s] = t / anchor
        links[s] = len(es)
        used_med[s] = float(np.median([e.used for e in es]))
        rms_med[s] = float(np.median([e.rms for e in es]))
        kept.append(s)

    return Ladder(
        stack=st.name,
        start=start,
        w=w,
        anchor=anchor,
        anchor_used=anchor_e.used,
        anchor_rms=anchor_e.rms,
        spans=kept,
        total=total,
        frac=frac,
        links=links,
        used_med=used_med,
        rms_med=rms_med,
    )


def pct(logmag: float) -> float:
    """A log-magnification as a percentage scale change."""
    return 100.0 * (math.exp(logmag) - 1.0)


def print_ladder(ld: Ladder, indent: str = "    ") -> None:
    print(f"{indent}window {ld.start}..{ld.start + ld.w}   "
          f"anchor A_W = {pct(ld.anchor):+.4f}%  "
          f"({ld.anchor_used} tiles, rms {ld.anchor_rms:.2f})   "
          f"true rate {1e3 * ld.rate_true:+.4f}e-3/frame")
    print(f"{indent}{'span':>5} {'links':>6} {'T_W(s) %':>12} {'S_W(s)':>9} "
          f"{'1/S':>7} {'d_true px':>10} {'med_used':>9} {'med_rms':>8}")
    for s in ld.spans:
        inv = 1.0 / ld.frac[s] if ld.frac[s] else float("nan")
        print(f"{indent}{s:>5} {ld.links[s]:>6} {pct(ld.total[s]):>12.4f} "
              f"{ld.frac[s]:>9.4f} {inv:>7.3f} {ld.disp_true(s):>10.3f} "
              f"{ld.used_med[s]:>9.0f} {ld.rms_med[s]:>8.3f}")
