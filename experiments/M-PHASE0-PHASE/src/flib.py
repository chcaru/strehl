"""Cycle consistency of the raw alignment edges, by span and by field radius.

The census measures what registration accuracy the unfolding *needs*. This
measures what the aligner can *achieve*, from the aligner's own measurements and
with no solver involved.

`crates/strehl-core/src/align.rs:2544-2551` states the principle:

    This is computed **from the data alone**, with no solver involved, so it
    bounds what any solver can achieve: if the measurements disagree with
    themselves by `x` px around a closed loop, no reconciliation of them can be
    right to better than about `x`.

`strehl align` already prints a single pooled number for this ("cycle-consistency
floor"), but pooled over every span in `[1, 2, 4, 8, 16, 32, 64, 96, 128]`. Frames
within one depth of field are 1 to 8 apart, so the pooled figure is not the figure
C1 needs. This resolves it by span, and by field radius, because a similarity's
error grows linearly with distance from the plane centre and the census reports by
radius.

UNITS. Edge CSVs and this module work in PLANE px throughout. The plane is a 2x2
CFA bin, so one plane px is two sensor px, and the bar in `p1_bar.py` is in sensor
px. `to_sensor()` is the only place the factor is applied.
"""

import csv
import numpy as np

PLANE_TO_SENSOR = 2.0


def to_sensor(v):
    return np.asarray(v) * PLANE_TO_SENSOR


def load_edges(path, cfg=None):
    """Edges as {(i, j): (a, b)} with `a`, `b` complex, from an M10-format CSV.

    Columns `g, rot, ax, ay` are the linearised similarity readout that
    `align.rs:261-267` emits: `a = (1 + g) + i*rot`, `b = ax + i*ay`.
    """
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["status"] != "ok":
                continue
            if cfg is not None and r["cfg"] != cfg:
                continue
            i, j = int(r["ref"]), int(r["mov"])
            a = complex(1.0 + float(r["g"]), float(r["rot"]))
            b = complex(float(r["ax"]), float(r["ay"]))
            out[(i, j)] = (a, b)
    return out


def plane_of(path):
    with open(path, newline="") as f:
        r = next(csv.DictReader(f))
        return int(r["plane_w"]), int(r["plane_h"])


def then(t1, t2):
    """`align.rs`: (self then other).a = self.a*other.a, .b = other.a*self.b + other.b."""
    a1, b1 = t1
    a2, b2 = t2
    return (a1 * a2, a2 * b1 + b2)


def corners(plane):
    w, h = float(plane[0]), float(plane[1])
    cx, cy = w * 0.5, h * 0.5
    return np.array([complex(-cx, -cy), complex(w - cx, -cy),
                     complex(-cx, h - cy), complex(w - cx, h - cy)])


def corner_radius(plane):
    return float(np.hypot(plane[0], plane[1]) * 0.5)


def corner_err(t1, t2, plane):
    da = t1[0] - t2[0]
    db = t1[1] - t2[1]
    return float(np.max(np.abs(da * corners(plane) + db)))


def err_at_radius(t1, t2, r):
    """Worst displacement at field radius `r`, plane px.

    `|da*p + db|` over all `p` with `|p| = r` is maximised at `|da|*r + |db|`,
    attained where `da*p` is parallel to `db`. At the corner radius this equals
    `corner_err` only when a corner happens to lie in that direction, so
    `err_at_radius(corner_radius)` is an upper bound on `corner_err`, never below
    it. Control C-R pins that relation.
    """
    da = t1[0] - t2[0]
    db = t1[1] - t2[1]
    return float(abs(da) * r + abs(db))


def triples(edges):
    """Every `i < j < k` with all three edges measured, as `align.rs` enumerates."""
    out = []
    by_i = {}
    for (i, j) in edges:
        by_i.setdefault(i, []).append(j)
    for v in by_i.values():
        v.sort()
    for (i, k) in sorted(edges):
        for j in by_i.get(i, []):
            if i < j < k and (j, k) in edges:
                out.append((i, j, k))
    return out


def cycle_errors(edges, plane, radii=None, max_triples=0):
    """Per-triple cycle error. Returns a dict of parallel arrays.

    `max_triples` reproduces the binary's deterministic stride subsample, so the
    shipped `cycle-floor-px` can be reproduced exactly (control C-C).
    """
    trip = triples(edges)
    if max_triples and len(trip) > max_triples:
        stride = -(-len(trip) // max_triples)
        trip = trip[::stride]
    rc = corner_radius(plane)
    out = dict(i=[], j=[], k=[], span=[], err=[], err_scale=[], err_trans=[])
    if radii is not None:
        out["at_radius"] = []
    for (i, j, k) in trip:
        direct = edges[(i, k)]
        chained = then(edges[(i, j)], edges[(j, k)])
        da = abs(direct[0] - chained[0])
        db = abs(direct[1] - chained[1])
        out["i"].append(i)
        out["j"].append(j)
        out["k"].append(k)
        out["span"].append(k - i)
        out["err"].append(corner_err(direct, chained, plane))
        out["err_scale"].append(rc * da)
        out["err_trans"].append(db)
        if radii is not None:
            out["at_radius"].append([da * r + db for r in radii])
    for key in out:
        out[key] = np.asarray(out[key])
    return out


def synth_consistent(n, rng, plane):
    """A perfectly self-consistent edge set: every edge is exactly `gi^-1 then gj`.

    Cycle consistency must read zero on this by construction, which is what
    control C-N asserts and what `align.rs:3431` asserts on the Rust side.
    """
    g = []
    w, h = plane
    for _ in range(n):
        a = complex(1.0 + rng.normal(0, 1e-3), rng.normal(0, 1e-4))
        b = complex(rng.normal(0, 5.0), rng.normal(0, 5.0))
        g.append((a, b))
    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            ai, bi = g[i]
            inv = (1.0 / ai, -bi / ai)
            edges[(i, j)] = then(inv, g[j])
    return edges, g
