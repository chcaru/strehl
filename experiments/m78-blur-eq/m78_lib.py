"""M12 (harness copied verbatim from M10) — deep-stack alignment: similarity algebra, global solvers, and metrics.

A similarity is the complex pair ``(a, b)`` acting on plane coordinates ``p``
taken **relative to the plane centre**::

    p' = a * p + b

The Rust harness's ``Fit{g, rot, ax, ay}`` maps to ``a = (1+g) + 1j*rot``,
``b = ax + 1j*ay``.  Composition of ``t1`` then ``t2`` is
``a = a1*a2, b = a2*b1 + b2``.

``M(i->j)`` is a **measured** edge taking frame-``i`` coordinates to frame-``j``
coordinates.  ``G_j = (A_j, B_j)`` is a **global** transform taking frame-0
coordinates to frame ``j``, with the gauge ``G_0 = (1, 0)``.  An edge asserts::

    A_j = a_ij * A_i          B_j = a_ij * B_i + b_ij

Both are *linear* in the unknowns, so the whole bundle adjustment is one complex
linear least-squares problem.

No I/O beyond CSV reads.  Nothing here touches the capture directories.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

PLANE_W = 3516
PLANE_H = 2344

IDENT = (1.0 + 0.0j, 0.0 + 0.0j)


def corners(w: int = PLANE_W, h: int = PLANE_H) -> np.ndarray:
    """The four plane corners as complex offsets from the plane centre."""
    cx, cy = w * 0.5, h * 0.5
    return np.array(
        [
            (0 - cx) + 1j * (0 - cy),
            (w - cx) + 1j * (0 - cy),
            (0 - cx) + 1j * (h - cy),
            (w - cx) + 1j * (h - cy),
        ]
    )


def corner_radius(w: int = PLANE_W, h: int = PLANE_H) -> float:
    return math.hypot(w, h) * 0.5


CORNERS = corners()
RHO = corner_radius()


def fit_to_ab(g: float, rot: float, ax: float, ay: float) -> tuple[complex, complex]:
    return (1.0 + g) + 1j * rot, ax + 1j * ay


def ab_to_fit(t: tuple[complex, complex]) -> tuple[float, float, float, float]:
    a, b = t
    return a.real - 1.0, a.imag, b.real, b.imag


def compose(t1, t2):
    """Apply ``t1`` first, then ``t2``."""
    a1, b1 = t1
    a2, b2 = t2
    return a1 * a2, a2 * b1 + b2


def invert(t):
    a, b = t
    return 1.0 / a, -b / a


def relative(gi, gj):
    """The transform taking frame ``i`` coordinates to frame ``j`` coordinates,
    given both frames' global transforms."""
    return compose(invert(gi), gj)


def corner_err(t1, t2) -> float:
    """Largest difference, over the four plane corners, in where two similarities
    send a corner. Plane px.

    This is the *reported* statistic throughout M10 — the worst corner, which is
    the conservative choice and the one M3 and M6 quoted. It is deliberately not
    the quantity the least-squares objective minimises; see `corner_err_rms`.
    """
    da = t1[0] - t2[0]
    db = t1[1] - t2[1]
    return float(np.max(np.abs(da * CORNERS + db)))


def corner_err_rms(t1, t2) -> float:
    """Root-mean-square difference over the four plane corners. Plane px.

    This is exactly what the weighted least squares minimises, because the
    corner set is symmetric about the plane centre (``sum(p) = 0`` and
    ``mean|p|^2 = RHO^2``), so the cross term vanishes and

        mean_corners |da*p + db|^2  ==  RHO^2 |da|^2 + |db|^2

    identically. `m10_selftest.py` checks that identity numerically rather than
    taking it on trust.
    """
    da = t1[0] - t2[0]
    db = t1[1] - t2[1]
    return float(math.sqrt(float(np.mean(np.abs(da * CORNERS + db) ** 2))))


def corner_err_parts(t1, t2) -> tuple[float, float]:
    """Corner error split into its scale/rotation part and its translation part.
    ``(rho*|da|, |db|)``. Reported separately because they have different
    error mechanisms: ``da`` carries pixel locking's compounding bias, ``db``
    does not."""
    da = t1[0] - t2[0]
    db = t1[1] - t2[1]
    return float(RHO * abs(da)), float(abs(db))


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------


@dataclass
class Edge:
    i: int
    j: int
    span: int
    ok: bool
    a: complex
    b: complex
    rms: float
    used: int
    raw_n: int
    total: int
    lever: float
    peak: float
    cfg: str
    case: str

    def t(self):
        return (self.a, self.b)


def _f(row, key, default=float("nan")):
    v = row.get(key, "")
    if v is None or v == "":
        return default
    return float(v)


def read_edges(path: str, cfg: str | None = None) -> list[Edge]:
    out: list[Edge] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if cfg is not None and row["cfg"] != cfg:
                continue
            ok = row["status"] == "ok"
            g, rot = _f(row, "g", 0.0), _f(row, "rot", 0.0)
            ax, ay = _f(row, "ax", 0.0), _f(row, "ay", 0.0)
            a, b = fit_to_ab(g, rot, ax, ay)
            out.append(
                Edge(
                    i=int(row["ref"]),
                    j=int(row["mov"]),
                    span=int(row["span"]),
                    ok=ok,
                    a=a,
                    b=b,
                    rms=_f(row, "rms"),
                    used=int(row["used"]),
                    raw_n=int(row["raw_n"]),
                    total=int(row["total"]),
                    lever=_f(row, "lever_rms"),
                    peak=_f(row, "peak_mean"),
                    cfg=row["cfg"],
                    case=row["case"],
                )
            )
    return out


def read_floor(path: str) -> list[dict]:
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            ok = row["g"] != ""
            out.append(
                dict(
                    base=int(row["base_frame"]),
                    warp=int(row["warp_id"]),
                    margin=int(row["margin"]),
                    cfg=row.get("cfg", "m10"),
                    g_true=float(row["g_true"]),
                    ok=ok,
                    corner_err=_f(row, "corner_err"),
                    rms=_f(row, "rms"),
                    used=int(row["used"]),
                )
            )
    return out


def read_truth(path: str) -> dict[int, tuple[complex, complex]]:
    out = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            out[int(row["frame"])] = fit_to_ab(
                float(row["g"]), float(row["rot"]), float(row["ax"]), float(row["ay"])
            )
    return out


# --------------------------------------------------------------------------
# weights
# --------------------------------------------------------------------------


def edge_sigmas(e: Edge, scheme: str = "invvar") -> tuple[float, float]:
    """Per-edge standard errors ``(sigma_A_px, sigma_B_px)`` in plane px at the
    corner radius.

    ``invvar`` derives them from the fit's own statistics: the standard error of
    a least-squares translation is ``rms/sqrt(used)``, and of the scale term
    ``rms/(lever*sqrt(used))``, which becomes ``rho*rms/(lever*sqrt(used))`` px
    at the corner.  ``unit`` gives every edge the same weight; ``count`` uses
    only the tile count.  All three are reported, because ``rms`` is inflated on
    long-span pairs by M6's blur-induced correlation bias, so inverse-variance
    weighting could quietly discard exactly the long edges that break the
    chaining degeneracy.
    """
    if scheme == "unit":
        return 1.0, 1.0
    if scheme == "count":
        n = max(e.used, 1)
        return 1.0 / math.sqrt(n), 1.0 / math.sqrt(n)
    n = max(e.used, 1)
    lever = e.lever if (e.lever and e.lever > 1.0) else 1000.0
    rms = e.rms if (e.rms and e.rms > 1e-6) else 0.19
    sb = rms / math.sqrt(n)
    sa = RHO * rms / (lever * math.sqrt(n))
    return sa, sb


# --------------------------------------------------------------------------
# solvers.  Every solver returns a list of length n of (a, b) or None.
# --------------------------------------------------------------------------


def _edge_map(edges: list[Edge]) -> dict[tuple[int, int], Edge]:
    m: dict[tuple[int, int], Edge] = {}
    for e in edges:
        if not e.ok:
            continue
        key = (e.i, e.j)
        prev = m.get(key)
        if prev is None or e.used > prev.used:
            m[key] = e
    return m


def solve_fixed(edges: list[Edge], n: int):
    """`S0-fixed` — the status quo (AGENTS.md rule 6): every frame aligned
    directly to frame 0. Frames whose direct fit failed have no transform."""
    m = _edge_map(edges)
    g = [None] * n
    g[0] = IDENT
    for j in range(1, n):
        e = m.get((0, j))
        if e is not None:
            g[j] = e.t()
    return g


def solve_hops(edges: list[Edge], n: int, max_span: int):
    """`S1`/`S2` — minimum-hop composition over edges of span <= ``max_span``.

    ``max_span=1`` is the adjacent chain that AGENTS.md rule 6 forbids.  Larger
    ``max_span`` is candidate (a), the hierarchical keyframe ladder, in its
    most favourable form: a breadth-first tree from frame 0 minimises the number
    of compositions to every frame, so it minimises the number of times a
    per-step bias can compound.
    """
    m = _edge_map(edges)
    adj: dict[int, list[tuple[int, int, tuple[complex, complex]]]] = defaultdict(list)
    for (i, j), e in m.items():
        if e.span > max_span:
            continue
        adj[i].append((j, e.span, e.t()))
        adj[j].append((i, e.span, invert(e.t())))
    # Registered tie-break (amendment A1): among equal-hop arrivals prefer the
    # longest available span, then the lowest neighbour index.
    for k in adj:
        adj[k].sort(key=lambda z: (-z[1], z[0]))

    g = [None] * n
    g[0] = IDENT
    hops = [0] * n
    q = deque([0])
    seen = {0}
    while q:
        u = q.popleft()
        for v, _s, t in adj[u]:
            if v in seen:
                continue
            seen.add(v)
            g[v] = compose(g[u], t)
            hops[v] = hops[u] + 1
            q.append(v)
    return g, hops


def build_ls(
    edges: list[Edge],
    n: int,
    scheme: str = "invvar",
    weights: dict[tuple[int, int], float] | None = None,
    smooth: float = 0.0,
):
    """Assemble the complex linear system for the bundle adjustment.

    Unknown vector is ``[A_1..A_{n-1}, B_1..B_{n-1}]``; ``A_0 = 1``, ``B_0 = 0``
    is the gauge.  Row pairs are the two edge constraints, each divided by its
    own standard error so the system is in units of plane px at the corner.
    """
    ncol = 2 * (n - 1)
    rows_m: list[np.ndarray] = []
    rows_b: list[complex] = []
    row_edge: list[int] = []

    def col_a(k):
        return k - 1

    def col_b(k):
        return (n - 1) + k - 1

    for idx, e in enumerate(edges):
        if not e.ok:
            continue
        sa, sb = edge_sigmas(e, scheme)
        extra = 1.0 if weights is None else weights.get((e.i, e.j), 1.0)
        if extra <= 0.0:
            continue
        wa = math.sqrt(extra) * RHO / max(sa, 1e-9)
        wb = math.sqrt(extra) / max(sb, 1e-9)

        r = np.zeros(ncol, dtype=complex)
        rhs = 0.0 + 0.0j
        if e.i == 0:
            rhs -= e.a
        else:
            r[col_a(e.i)] += e.a
        r[col_a(e.j)] -= 1.0
        rows_m.append(r * wa)
        rows_b.append(rhs * wa)
        row_edge.append(idx)

        r = np.zeros(ncol, dtype=complex)
        rhs = -e.b
        if e.i != 0:
            r[col_b(e.i)] += e.a
        r[col_b(e.j)] -= 1.0
        rows_m.append(r * wb)
        rows_b.append(rhs * wb)
        row_edge.append(idx)

    if smooth > 0.0:
        for k in range(1, n - 1):
            r = np.zeros(ncol, dtype=complex)
            rhs = 0.0 + 0.0j
            for kk, c in ((k - 1, 1.0), (k, -2.0), (k + 1, 1.0)):
                if kk == 0:
                    rhs -= c * 1.0
                else:
                    r[col_a(kk)] += c
            rows_m.append(r * smooth * RHO)
            rows_b.append(rhs * smooth * RHO)
            row_edge.append(-1)

            r = np.zeros(ncol, dtype=complex)
            rhs = 0.0 + 0.0j
            for kk, c in ((k - 1, 1.0), (k, -2.0), (k + 1, 1.0)):
                if kk != 0:
                    r[col_b(kk)] += c
            rows_m.append(r * smooth)
            rows_b.append(rhs * smooth)
            row_edge.append(-1)

    return np.array(rows_m), np.array(rows_b), row_edge


def _unpack(x: np.ndarray, n: int):
    g = [IDENT]
    for k in range(1, n):
        g.append((x[k - 1], x[(n - 1) + k - 1]))
    return g


def _reachable(edges: list[Edge], n: int) -> list[bool]:
    """Frames connected to frame 0 through the measured edge graph.  Frames
    outside that component are not constrained by any edge relative to the
    anchor, so a least-squares solve returns an arbitrary minimum-norm value
    for them.  They must be reported as *not covered*, never as a number."""
    adj: dict[int, list[int]] = {k: [] for k in range(n)}
    for e in edges:
        if e.ok:
            adj[e.i].append(e.j)
            adj[e.j].append(e.i)
    seen = [False] * n
    seen[0] = True
    stack = [0]
    while stack:
        k = stack.pop()
        for m in adj[k]:
            if not seen[m]:
                seen[m] = True
                stack.append(m)
    return seen


def solve_ba(
    edges: list[Edge],
    n: int,
    scheme: str = "invvar",
    smooth: float = 0.0,
    robust: int = 3,
    huber_px: float = 3.0,
):
    """`S3` — global bundle adjustment.  Weighted complex linear least squares
    over every measured edge, with optional IRLS Huber re-weighting and an
    optional second-difference smoothness prior (`S6`)."""
    w: dict[tuple[int, int], float] = {}
    g = None
    reach = _reachable(edges, n)
    for _ in range(max(robust, 1)):
        m, b, _ = build_ls(edges, n, scheme, w if w else None, smooth)
        if m.size == 0:
            return None
        x, *_ = np.linalg.lstsq(m, b, rcond=None)
        g = _unpack(x, n)
        if robust <= 1:
            break
        w = {}
        for e in edges:
            if not e.ok:
                continue
            r = corner_err(relative(g[e.i], g[e.j]), e.t())
            w[(e.i, e.j)] = 1.0 if r <= huber_px else (huber_px / r)
    if g is None:
        return None
    if smooth <= 0.0:
        g = [g[k] if reach[k] else None for k in range(n)]
    return g


# --------------------------------------------------------------------------
# candidate (c): a parametric model in stack index
# --------------------------------------------------------------------------


def poly_basis(j: int, deg: int, n: int) -> np.ndarray:
    """Basis with no constant term, so ``P(0) = 0`` by construction."""
    t = j / max(n - 1, 1)
    return np.array([t**k for k in range(1, deg + 1)])


def solve_poly(
    edges: list[Edge],
    n: int,
    deg: int,
    scheme: str = "invvar",
    fixed_centre: bool = False,
    bdeg: int | None = None,
    robust: int = 3,
    huber_px: float = 3.0,
):
    """`S4`/`S5` — candidate (c).

    ``log A_j = P(j)`` for a complex polynomial ``P`` with ``P(0) = 0``, fitted
    directly to the edge constraints ``log a_ij = P(j) - P(i)``.  Then ``B_j``
    is either free (``bdeg=None``, the weakest parametric claim), a complex
    polynomial of degree ``bdeg`` with ``B_0 = 0`` (the true candidate (c)), or
    ``B_j = (1 - A_j) * c`` for a single complex scale centre ``c`` (``S5``,
    the strongest claim: pure magnification about a fixed point).

    The ``log`` is safe: ``|a - 1| <= 0.06`` over the whole stack, so the
    principal branch is unambiguous and no unwrapping is needed.
    """
    w: dict[tuple[int, int], float] = {}
    coef = None
    for _ in range(max(robust, 1)):
        rows, rhs = [], []
        for e in edges:
            if not e.ok:
                continue
            sa, _ = edge_sigmas(e, scheme)
            extra = w.get((e.i, e.j), 1.0)
            if extra <= 0.0:
                continue
            wa = math.sqrt(extra) * RHO / max(sa, 1e-9)
            rows.append((poly_basis(e.j, deg, n) - poly_basis(e.i, deg, n)) * wa)
            rhs.append(np.log(e.a) * wa)
        if not rows:
            return None
        coef, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
        A = [complex(np.exp(poly_basis(j, deg, n) @ coef)) for j in range(n)]
        if robust <= 1:
            break
        w = {}
        for e in edges:
            if not e.ok:
                continue
            r = RHO * abs(e.a * A[e.i] - A[e.j])
            w[(e.i, e.j)] = 1.0 if r <= huber_px else (huber_px / r)

    A = [complex(np.exp(poly_basis(j, deg, n) @ coef)) for j in range(n)]
    A[0] = 1.0 + 0.0j

    if fixed_centre:
        rows, rhs = [], []
        for e in edges:
            if not e.ok:
                continue
            _, sb = edge_sigmas(e, scheme)
            wb = 1.0 / max(sb, 1e-9)
            rows.append([(e.a * (1.0 - A[e.i]) - (1.0 - A[e.j])) * wb])
            rhs.append(-e.b * wb)
        c, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
        c = complex(c[0])
        return [(A[j], (1.0 - A[j]) * c) for j in range(n)], c

    ncol = (n - 1) if bdeg is None else bdeg
    rows, rhs = [], []
    for e in edges:
        if not e.ok:
            continue
        _, sb = edge_sigmas(e, scheme)
        wb = 1.0 / max(sb, 1e-9)
        r = np.zeros(ncol, dtype=complex)
        v = -e.b
        if bdeg is None:
            if e.i != 0:
                r[e.i - 1] += e.a
            r[e.j - 1] -= 1.0
        else:
            r += e.a * poly_basis(e.i, bdeg, n) - poly_basis(e.j, bdeg, n)
        rows.append(r * wb)
        rhs.append(v * wb)
    x, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    if bdeg is None:
        B = [0.0 + 0.0j] + [complex(v) for v in x]
    else:
        B = [complex(poly_basis(j, bdeg, n) @ x) for j in range(n)]
        B[0] = 0.0 + 0.0j
    return [(A[j], B[j]) for j in range(n)], None


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def graph_stats(edges: list[Edge], n: int) -> dict:
    """Cycle rank and connectivity.  A bundle adjustment over a **tree** is
    algebraically identical to chaining along that tree, so a design whose
    training graph is a tree is structurally incapable of separating the two.
    Every training subset in M10 reports this before it is believed."""
    ok = [e for e in edges if e.ok]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    uniq = {(e.i, e.j) for e in ok}
    for i, j in uniq:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    comps = len({find(k) for k in range(n)})
    reach = sum(1 for k in range(n) if find(k) == find(0))
    return dict(
        n_edges=len(uniq),
        n_frames=n,
        components=comps,
        cycle_rank=len(uniq) - (n - comps),
        reachable_from_0=reach,
        is_tree=(len(uniq) == n - comps),
    )


def predict(g, i: int, j: int):
    if g[i] is None or g[j] is None:
        return None
    return relative(g[i], g[j])


def edge_errors(g, edges: list[Edge]) -> list[tuple[Edge, float, float, float]]:
    """Corner error of every measured edge against a global solution."""
    out = []
    for e in edges:
        if not e.ok:
            continue
        p = predict(g, e.i, e.j)
        if p is None:
            continue
        ce = corner_err(p, e.t())
        pa, pb = corner_err_parts(p, e.t())
        out.append((e, ce, pa, pb))
    return out


def cycle_consistency(edges: list[Edge], max_triples: int = 20000, seed: int = 7):
    """`M1` — cycle consistency of the raw measurements.  For triples
    ``i<j<k`` with all three edges measured, corner error of ``M(i->k)``
    against ``M(j->k) o M(i->j)``.  Computed from data alone, so it bounds what
    any solver can achieve."""
    m = _edge_map(edges)
    by_i: dict[int, list[int]] = defaultdict(list)
    for i, j in m:
        by_i[i].append(j)
    rng = np.random.default_rng(seed)
    trip = []
    for (i, k), _ in m.items():
        for j in by_i.get(i, []):
            if i < j < k and (j, k) in m:
                trip.append((i, j, k))
    if len(trip) > max_triples:
        idx = rng.choice(len(trip), size=max_triples, replace=False)
        trip = [trip[t] for t in idx]
    out = []
    for i, j, k in trip:
        direct = m[(i, k)].t()
        chained = compose(m[(i, j)].t(), m[(j, k)].t())
        out.append(
            dict(
                i=i,
                j=j,
                k=k,
                span_ik=k - i,
                span_ij=j - i,
                span_jk=k - j,
                err=corner_err(direct, chained),
                err_scale=corner_err_parts(direct, chained)[0],
                err_trans=corner_err_parts(direct, chained)[1],
            )
        )
    return out


def summarise(vals) -> dict:
    v = np.asarray([x for x in vals if np.isfinite(x)], dtype=float)
    if v.size == 0:
        return dict(n=0, median=float("nan"), mean=float("nan"), p90=float("nan"), max=float("nan"), sd=float("nan"))
    return dict(
        n=int(v.size),
        median=float(np.median(v)),
        mean=float(np.mean(v)),
        p90=float(np.percentile(v, 90)),
        max=float(v.max()),
        sd=float(np.std(v, ddof=1)) if v.size > 1 else 0.0,
    )
