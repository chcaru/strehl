"""M16 -- orientation asymmetry and fixed-pattern noise: the analysis.

Reads only committed CSVs: this milestone's `data/A*-*.csv` and, for Gate 2,
M15's `experiments/m15-regulariser-window/data/edge-*.csv`. Anyone can rerun it
without running the harness.

Aggregation rule, M15's, restated once and used everywhere:

    cell             = (stack, geometry, step),  step > 0
    E(w, cell, g)    = mean over the 5 seeds of `excess_dn` at width g
    w*(cell, g)      = argmin_w E, ties to the smallest w
    shift(cell)      = w*(cell, 17) - w*(cell, 1)
    regret(w,cell,g) = E(w,cell,g) - min_w' E(w',cell,g)
    meanregret(w,g)  = mean of regret over the 30 step>0 cells

The primary statistic (PREREGISTRATION.md section 3.3):

    A = median shift(horizontal) - median shift(vertical UNION bar)
    U = fraction of horizontal cells whose shift is negative

Zero-step cells are the NULL and never enter a decision.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
M15_DATA = HERE.parent / "m15-regulariser-window" / "data"

LADDER = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 26, 33, 40]
GEOMS = ("horizontal", "vertical", "bar")

# M15's committed shared columns, in order. Gate 2 compares these as strings.
SHARED = [
    "stack", "shape", "frames", "w_near", "w_far", "step", "sigma0", "alpha",
    "noise_scale", "seed", "band", "measure", "family", "window",
    "support_radius", "width", "radius", "eff_radius", "acc", "acc_band",
    "bleed_bg", "bleed_fg", "mis_bg", "mis_fg", "dmae_band", "dmae_far",
    "excess_dn", "excess_sigma", "band_rms", "floor_rms", "far_rms",
    "peak_bias", "single_sigma",
]


def geometry(shape: str) -> str:
    return shape.split("@", 1)[0]


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Arm:
    """One arm's `excess_dn` surface, keyed for the statistics above."""

    def __init__(self, name: str, rows: list[dict]):
        self.name = name
        # (cell, width, window) -> {seed: excess}
        self.vals: dict = defaultdict(dict)
        self.meta: dict = {}
        for r in rows:
            cell = (r["stack"], geometry(r["shape"]), int(r["step"]))
            self.vals[(cell, int(r["width"]), int(r["window"]))][r["seed"]] = float(r["excess_dn"])
            if not self.meta:
                self.meta = {k: r.get(k, "") for k in
                             ("arm", "texture", "destripe", "fpn_sd", "fpn_axis",
                              "fpn_stage", "transpose", "score_w", "score_h", "base_frame")}
        self.cells = sorted({k[0] for k in self.vals})
        self.decision = [c for c in self.cells if c[2] > 0]
        self.seeds = sorted({s for d in self.vals.values() for s in d})

    def E(self, cell, g, w, drop_seed=None) -> float:
        d = self.vals[(cell, g, w)]
        vs = [v for s, v in d.items() if s != drop_seed]
        return sum(vs) / len(vs)

    def wstar(self, cell, g, drop_seed=None):
        best_w, best_v = None, None
        for w in LADDER:
            if (cell, g, w) not in self.vals:
                continue
            v = self.E(cell, g, w, drop_seed)
            if best_v is None or v < best_v:
                best_v, best_w = v, w
        return best_w, best_v

    def shifts(self, drop_seed=None) -> dict:
        return {c: self.wstar(c, 17, drop_seed)[0] - self.wstar(c, 1, drop_seed)[0]
                for c in self.decision}

    def A_and_U(self, drop_seed=None):
        sh = self.shifts(drop_seed)
        h = [v for c, v in sh.items() if c[1] == "horizontal"]
        vb = [v for c, v in sh.items() if c[1] in ("vertical", "bar")]
        if not h or not vb:
            return None, None, sh
        A = statistics.median(h) - statistics.median(vb)
        U = sum(1 for v in h if v < 0) / len(h)
        return A, U, sh

    def meanregret(self, g) -> dict:
        out = {}
        for w in LADDER:
            acc, n = 0.0, 0
            for c in self.decision:
                if (c, g, w) not in self.vals:
                    continue
                _, best = self.wstar(c, g)
                acc += self.E(c, g, w) - best
                n += 1
            if n:
                out[w] = acc / n
        return out

    def level(self, g, w) -> float:
        """Mean absolute E_excess over the decision cells, in DN. The
        'have I destroyed the signal' readout."""
        vs = [self.E(c, g, w) for c in self.decision if (c, g, w) in self.vals]
        return sum(vs) / len(vs) if vs else float("nan")


def load_arms() -> dict:
    arms = {}
    for path in sorted(DATA.glob("A*-*MSDCF.csv")):
        name = path.name.split("-")[0]
        arms.setdefault(name, []).extend(read(path))
    return {k: Arm(k, v) for k, v in sorted(arms.items())}


def binom_p(k: int, n: int) -> float:
    """Two-sided exact binomial sign test against p=0.5, ignoring ties."""
    if n == 0:
        return float("nan")
    def pmf(i):
        return math.comb(n, i) * 0.5 ** n
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def label_argmin(mr: dict) -> str:
    ws = [w for w in LADDER if w in mr]
    best = min(ws, key=lambda w: mr[w])
    if best in (ws[0], ws[-1]):
        return f"w{best} ENDPOINT (no turnover found within the sweep)"
    i = ws.index(best)
    sep = min(mr[ws[i - 1]], mr[ws[i + 1]]) - mr[best]
    return f"w{best} interior, separated from its better neighbour by {sep:.4f} DN"


# ------------------------------------------------------------------- gate 1

def gate1() -> bool:
    targets = {
        "bar": (10, 10.5, 12.0, 1.0, (2, 6, 2)),
        "horizontal": (10, 9.0, 7.0, -2.5, (10, 0, 0)),
        "vertical": (10, 17.0, 19.0, 1.5, (2, 6, 2)),
        "ALL": (30, 13.0, 12.0, 0.0, (14, 12, 4)),
    }
    rows = []
    for p in sorted(M15_DATA.glob("edge-*MSDCF.csv")):
        rows.extend(read(p))
    a = Arm("M15", rows)
    sh = a.shifts()
    w1 = {c: a.wstar(c, 1)[0] for c in a.decision}
    w17 = {c: a.wstar(c, 17)[0] for c in a.decision}
    print("GATE 1 -- reproduce SYNTHESIS fact 83 from M15's committed CSVs")
    print(f"  {'geometry':<12}{'n':>4}{'w*(1)':>8}{'w*(17)':>8}{'shift':>8}"
          f"{'narrow':>8}{'wide':>6}{'same':>6}   verdict")
    ok = True
    for g in ("bar", "horizontal", "vertical", "ALL"):
        cs = [c for c in a.decision if g == "ALL" or c[1] == g]
        got = (len(cs), statistics.median(w1[c] for c in cs),
               statistics.median(w17[c] for c in cs),
               statistics.median(sh[c] for c in cs),
               (sum(1 for c in cs if sh[c] < 0), sum(1 for c in cs if sh[c] > 0),
                sum(1 for c in cs if sh[c] == 0)))
        good = got == targets[g]
        ok &= good
        print(f"  {g:<12}{got[0]:>4}{got[1]:>8.1f}{got[2]:>8.1f}{got[3]:>+8.1f}"
              f"{got[4][0]:>8}{got[4][1]:>6}{got[4][2]:>6}   "
              f"{'MATCH' if good else 'MISMATCH want ' + str(targets[g])}")
    A, U, _ = a.A_and_U()
    print(f"  reference statistic: A_ref = {A:+.2f} windows, U_ref = {U:.2f}")
    print(f"  {'GATE 1 PASS' if ok else 'GATE 1 FAIL'}\n")
    return ok, A, U


# ------------------------------------------------------------------- gate 2

def gate2(arms: dict) -> bool:
    print("GATE 2 -- arm A0 reproduces M15's harness field for field")
    if "A0" not in arms:
        print("  A0 not present, SKIPPED\n")
        return False
    m15 = {}
    for p in sorted(M15_DATA.glob("edge-*MSDCF.csv")):
        for r in read(p):
            m15[(r["stack"], r["shape"], r["step"], r["seed"], r["measure"], r["width"])] = r
    mine = []
    for p in sorted(DATA.glob("A0-*MSDCF.csv")):
        mine.extend(read(p))
    checked = missing = bad = 0
    first_bad = None
    for r in mine:
        k = (r["stack"], r["shape"], r["step"], r["seed"], r["measure"], r["width"])
        ref = m15.get(k)
        if ref is None:
            missing += 1
            continue
        checked += 1
        for col in SHARED:
            if r[col] != ref[col]:
                bad += 1
                if first_bad is None:
                    first_bad = (k, col, r[col], ref[col])
                break
    print(f"  rows compared {checked}, absent from M15 {missing}, mismatched {bad}")
    if first_bad:
        k, col, got, want = first_bad
        print(f"  first mismatch at {k}: {col} = {got!r}, M15 has {want!r}")
    ok = checked > 0 and bad == 0 and missing == 0
    print("  Byte-level agreement on every shared field. This is a CONSISTENCY")
    print("  CHECK, not independent evidence (discipline 34 / 20).")
    print(f"  {'GATE 2 PASS' if ok else 'GATE 2 FAIL'}\n")
    return ok


# ------------------------------------------------------------------- tables

def table_asymmetry(arms: dict, A_ref: float):
    print("=" * 78)
    print("1. THE ORIENTATION ASYMMETRY, PER ARM")
    print("=" * 78)
    print("   A = median shift(horizontal) - median shift(vertical UNION bar), in windows.")
    print("   phi = leave-one-seed-out spread of A (max - min over the 5 subsets).")
    print("   A difference smaller than phi is NOT RESOLVED.\n")
    print(f"   {'arm':<8}{'texture':<8}{'destripe':<9}{'fpnDN':>7}{'sq':>3}{'tr':>3}"
          f"{'med_h':>7}{'med_vb':>8}{'A':>7}{'phi':>7}{'U_h':>6}{'p(h)':>8}  note")
    out = {}
    for name, a in arms.items():
        A, U, sh = a.A_and_U()
        if A is None:
            continue
        los = [a.A_and_U(s)[0] for s in a.seeds]
        phi = max(los) - min(los)
        h = [v for c, v in sh.items() if c[1] == "horizontal"]
        nneg = sum(1 for v in h if v < 0)
        npos = sum(1 for v in h if v > 0)
        p = binom_p(nneg, nneg + npos)
        vb = [v for c, v in sh.items() if c[1] in ("vertical", "bar")]
        sq = "Y" if a.meta.get("score_w") == a.meta.get("score_h") and \
             int(a.meta.get("score_w", 0)) == 256 else "-"
        out[name] = (A, phi, U)
        print(f"   {name:<8}{a.meta['texture']:<8}{a.meta['destripe']:<9}"
              f"{float(a.meta['fpn_sd']):>7.3f}{sq:>3}"
              f"{'Y' if a.meta['transpose'] == '1' else '-':>3}"
              f"{statistics.median(h):>7.1f}{statistics.median(vb):>8.1f}"
              f"{A:>+7.1f}{phi:>7.1f}{U:>6.2f}{p:>8.4f}")
    print(f"\n   M15's committed surface, same statistic: A_ref = {A_ref:+.1f}")
    return out


def table_geometry(arms: dict):
    print("\n" + "=" * 78)
    print("2. PER-GEOMETRY BREAKDOWN (the fact-83 table, per arm)")
    print("=" * 78)
    for name, a in arms.items():
        sh = a.shifts()
        print(f"\n   {name}  texture={a.meta['texture']} destripe={a.meta['destripe']} "
              f"fpn={a.meta['fpn_sd']}DN/{a.meta['fpn_axis']}/{a.meta['fpn_stage']} "
              f"transpose={a.meta['transpose']} scored={a.meta['score_w']}x{a.meta['score_h']}")
        print(f"     {'geometry':<12}{'n':>3}{'w*(1)':>8}{'w*(17)':>8}{'shift':>8}"
              f"{'narrow':>8}{'wide':>6}{'same':>6}")
        for g in list(GEOMS) + ["ALL"]:
            cs = [c for c in a.decision if g == "ALL" or c[1] == g]
            if not cs:
                continue
            w1 = [a.wstar(c, 1)[0] for c in cs]
            w17 = [a.wstar(c, 17)[0] for c in cs]
            s = [sh[c] for c in cs]
            print(f"     {g:<12}{len(cs):>3}{statistics.median(w1):>8.1f}"
                  f"{statistics.median(w17):>8.1f}{statistics.median(s):>+8.1f}"
                  f"{sum(1 for v in s if v < 0):>8}{sum(1 for v in s if v > 0):>6}"
                  f"{sum(1 for v in s if v == 0):>6}")


def table_controls(arms: dict):
    print("\n" + "=" * 78)
    print("3. CONTROLS -- have I destroyed the signal? (P3, P4)")
    print("=" * 78)
    print("   level = mean E_excess over the 30 decision cells, in DN.")
    print("   P3 wants the level within 20% and the argmin within +-3 windows of")
    print("   the matching untreated arm. P4 wants the aggregate argmin interior.\n")
    base = {"A1": "A0", "A2": "A0", "A5x64": "A4x64", "A5x64o": "A4x64",
            "A9": "A6", "A3": None, "A0": None}
    print(f"   {'arm':<8}{'lvl@w13,g1':>12}{'lvl@w13,g17':>13}{'vs base':>9}   aggregate argmin at g=17")
    for name, a in arms.items():
        l1 = a.level(1, 13)
        l17 = a.level(17, 13)
        b = base.get(name)
        rel = ""
        if b and b in arms:
            lb = arms[b].level(17, 13)
            rel = f"{100 * (l17 - lb) / lb:+.1f}%"
        print(f"   {name:<8}{l1:>12.3f}{l17:>13.3f}{rel:>9}   {label_argmin(a.meanregret(17))}")


def table_transpose(arms: dict):
    print("\n" + "=" * 78)
    print("4. THE TRANSPOSE TEST -- does the asymmetry rotate with the scene?")
    print("=" * 78)
    if "A6" not in arms or "A8" not in arms:
        print("   A6 or A8 absent, SKIPPED")
        return
    a6, a8 = arms["A6"], arms["A8"]
    s6, s8 = a6.shifts(), a8.shifts()
    print("   A6 is a square ROI, untransposed. A8 is the same machinery with the")
    print("   textures transposed, so the SCENE rotates and the MACHINERY does not.")
    print("   If the asymmetry follows the scene, A8's horizontal behaves like A6's")
    print("   vertical. If it follows the machinery, A8 == A6.\n")
    print(f"   {'geometry':<12}{'A6 med shift':>14}{'A8 med shift':>14}{'A6 med w*(1)':>14}{'A8 med w*(1)':>14}")
    for g in GEOMS:
        cs6 = [c for c in a6.decision if c[1] == g]
        cs8 = [c for c in a8.decision if c[1] == g]
        print(f"   {g:<12}{statistics.median(s6[c] for c in cs6):>+14.1f}"
              f"{statistics.median(s8[c] for c in cs8):>+14.1f}"
              f"{statistics.median(a6.wstar(c, 1)[0] for c in cs6):>14.1f}"
              f"{statistics.median(a8.wstar(c, 1)[0] for c in cs8):>14.1f}")
    # cell-for-cell: does A8 equal A6 (machinery) or its rotation (scene)?
    same = [abs(s8[c] - s6[c]) for c in a6.decision if c in s8]
    rot = []
    for c in a6.decision:
        st, g, sp = c
        other = {"horizontal": "vertical", "vertical": "horizontal", "bar": "bar"}[g]
        k = (st, other, sp)
        if k in s8:
            rot.append(abs(s8[k] - s6[c]))
    print(f"\n   median |shift(A8, same geometry)   - shift(A6)| = {statistics.median(same):.1f}")
    print(f"   median |shift(A8, rotated geometry)- shift(A6)| = {statistics.median(rot):.1f}")
    print("   The smaller one names what the asymmetry is bolted to.")


def table_window_radius(arms: dict):
    print("\n" + "=" * 78)
    print("5. DOES WINDOW_RADIUS = 13 SURVIVE?")
    print("=" * 78)
    print("   meanregret(w, g) over the 30 decision cells. The shipped radius is 13.")
    print("   Registered rule: 13 changes only if the corrected argmin leaves M13's")
    print("   published basin w11-w15 AND meanregret(13) - min exceeds 0.87 DN.\n")
    print(f"   {'arm':<8}{'g':>3}{'argmin':>8}{'mr(argmin)':>12}{'mr(w13)':>10}"
          f"{'penalty':>10}{'basin?':>8}  label")
    for name, a in arms.items():
        for g in (1, 17):
            mr = a.meanregret(g)
            if 13 not in mr:
                continue
            ws = [w for w in LADDER if w in mr]
            best = min(ws, key=lambda w: mr[w])
            pen = mr[13] - mr[best]
            inb = "yes" if 11 <= best <= 15 else "NO"
            print(f"   {name:<8}{g:>3}{best:>8}{mr[best]:>12.4f}{mr[13]:>10.4f}"
                  f"{pen:>10.4f}{inb:>8}  {label_argmin(mr)}")


def table_null(arms: dict):
    print("\n" + "=" * 78)
    print("6. NULL CONTROL N3 -- the zero-step stratum")
    print("=" * 78)
    print("   These cells have an intensity edge, two textures and the whole")
    print("   compositing path, but NO depth discontinuity. If the orientation")
    print("   asymmetry is about occlusion, it must be weaker here.\n")
    print(f"   {'arm':<8}{'med_h':>8}{'med_vb':>8}{'A0step':>8}   per-geometry median w*(1)")
    for name, a in arms.items():
        zero = [c for c in a.cells if c[2] == 0]
        if not zero:
            continue
        sh = {c: a.wstar(c, 17)[0] - a.wstar(c, 1)[0] for c in zero}
        h = [v for c, v in sh.items() if c[1] == "horizontal"]
        vb = [v for c, v in sh.items() if c[1] in ("vertical", "bar")]
        if not h or not vb:
            continue
        lv = ", ".join(f"{g}={statistics.median(a.wstar(c, 1)[0] for c in zero if c[1] == g):.0f}"
                       for g in GEOMS)
        print(f"   {name:<8}{statistics.median(h):>8.1f}{statistics.median(vb):>8.1f}"
              f"{statistics.median(h) - statistics.median(vb):>+8.1f}   {lv}")


def table_positive_control(arms: dict, A_ref: float):
    print("\n" + "=" * 78)
    print("7. POSITIVE CONTROL P1/P2 -- can a planted row FPN move the asymmetry?")
    print("=" * 78)
    print("   A3 is the isotropic synthetic plant with no FPN. A4xK adds a row")
    print("   pattern of K x 0.377 DN to every frame the operator sees -- exactly")
    print("   H3's mechanism, and nothing else. A5 removes it again.")
    print("   If NO amplitude moves A, the plant cannot express H3 and the H3 arms")
    print("   carry no information (project rule 13 / discipline 24).\n")
    print(f"   {'arm':<8}{'fpn sd DN':>10}{'A':>7}{'phi':>7}{'U_h':>6}{'dA vs A3':>10}"
          f"{'lvl@w13':>10}")
    ref = arms.get("A3")
    refA = ref.A_and_U()[0] if ref else None
    for name in ("A3", "A4x1", "A4x8", "A4x64", "A5x64", "A5x64o", "A7"):
        a = arms.get(name)
        if a is None:
            continue
        A, U, _ = a.A_and_U()
        los = [a.A_and_U(s)[0] for s in a.seeds]
        phi = max(los) - min(los)
        d = f"{A - refA:+.1f}" if refA is not None else ""
        print(f"   {name:<8}{float(a.meta['fpn_sd']):>10.3f}{A:>+7.1f}{phi:>7.1f}"
              f"{U:>6.2f}{d:>10}{a.level(17, 13):>10.3f}")


def verdicts(arms: dict, stats: dict, A_ref: float):
    print("\n" + "=" * 78)
    print("8. THE PRE-REGISTERED DECISION RULES, APPLIED MECHANICALLY")
    print("=" * 78)
    if "A0" not in stats:
        print("   A0 absent; no control value; nothing decidable.")
        return
    A_ctrl, phi_ctrl, U_ctrl = stats["A0"]
    print(f"   A_ctrl = {A_ctrl:+.1f} (arm A0), phi_ctrl = {phi_ctrl:.1f}, U_ctrl = {U_ctrl:.2f}\n")

    def frac(name):
        if name not in stats or A_ctrl == 0:
            return None
        return abs(stats[name][0]) / abs(A_ctrl)

    # H3
    fired = []
    if "A3" in stats:
        a3 = stats["A3"][0]
        for k in ("A4x1", "A4x8", "A4x64"):
            if k in stats:
                a = arms[k]
                phi = stats[k][1]
                if abs(stats[k][0] - a3) > max(phi, stats["A3"][1]):
                    fired.append((k, stats[k][0] - a3))
    print(f"   P1 (the plant can express H3): {'FIRED at ' + ', '.join(f'{k} dA={d:+.1f}' for k, d in fired) if fired else 'DID NOT FIRE at any amplitude'}")
    for name, label in (("A1", "destripe mean"), ("A2", "destripe hp")):
        f = frac(name)
        if f is None:
            continue
        U = stats[name][2]
        if not fired:
            v = "NOT MEASURED (P1 did not fire)"
        elif f <= 0.5 and U <= 0.7:
            v = "SUPPORTED"
        elif f >= 0.75 and U >= 0.9:
            v = "REFUTED"
        else:
            v = "UNRESOLVED"
        print(f"   H3 via {name} ({label}): |A|/|A_ctrl| = {f:.2f}, U = {U:.2f}  ->  {v}")

    # H1
    if "A3" in stats:
        f = frac("A3")
        A3, phi3, U3 = stats["A3"]
        same_sign = (A3 < 0) == (A_ctrl < 0)
        if f >= 0.5 and same_sign and U3 >= 0.8:
            v = "REFUTED (the asymmetry survives on isotropic texture)"
        elif f <= 0.25:
            v = "SUPPORTED (the asymmetry vanishes on isotropic texture)"
        else:
            v = "UNRESOLVED"
        print(f"\n   H1 (texture anisotropy): A(A3) = {A3:+.1f}, |A|/|A_ctrl| = {f:.2f}, "
              f"U = {U3:.2f}, sign {'same' if same_sign else 'opposite'}  ->  {v}")

    # H2
    if "A6" in stats:
        f = frac("A6")
        print(f"   H2 (evaluation geometry): A(A6 square) = {stats['A6'][0]:+.1f}, "
              f"|A|/|A_ctrl| = {f:.2f}")
        if "A10" in stats:
            print(f"     H2a probe A10 (square scored band, rect plant): "
                  f"A = {stats['A10'][0]:+.1f}, |A|/|A_ctrl| = {frac('A10'):.2f}")
    if "A7" in stats:
        A7, phi7, _ = stats["A7"]
        v = "PASS" if abs(A7) <= max(phi7, 1.0) else "FAIL -- the machinery is asymmetric"
        print(f"   N4 (square + isotropic must be symmetric): A(A7) = {A7:+.1f}, "
              f"phi = {phi7:.1f}  ->  {v}")


def main() -> int:
    ok1, A_ref, U_ref = gate1()
    if not ok1:
        print("Gate 1 failed. Nothing downstream is valid.")
        return 1
    arms = load_arms()
    if not arms:
        print("No arm CSVs under data/. Run run-m16.ps1 first.")
        return 1
    print(f"loaded {len(arms)} arms: {', '.join(arms)}\n")
    gate2(arms)
    stats = table_asymmetry(arms, A_ref)
    table_geometry(arms)
    table_controls(arms)
    table_transpose(arms)
    table_positive_control(arms, A_ref)
    table_null(arms)
    table_window_radius(arms)
    verdicts(arms, stats, A_ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
