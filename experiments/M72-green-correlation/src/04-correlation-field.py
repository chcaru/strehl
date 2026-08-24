"""M72 step 4 -- POST-HOC.  The full temporal-noise correlation field.

Declared and committed BEFORE running, with checks that can fail and can
invalidate my own pre-registered C2 verdict.

WHY THIS EXISTS.  C2 returned GREEN-SPECIFIC (H2): at ISO 100,
rho(G1,G2) = +0.0826 against the matched diagonal control rho(R,B) = +0.0096.
The control could have failed and did not.  But O5, which was pre-registered
for a different purpose, reports that EVERY plane is temporally correlated
with its own in-plane neighbours at +0.05 to +0.16:

    ISO 100   R row/col +0.0756/+0.0647   G1 +0.0821/+0.0642
              G2 +0.0819/+0.0639          B  +0.1624/+0.0890

rho(G1,G2) = +0.0826 sits INSIDE that range rather than above it.  A reader
handed only C2 would conclude the two greens share something the other
planes do not.  O5 says the sensor has a broad local temporal correlation
structure and the green pair may be one cell of it.  Those are different
claims with different model consequences and I am not entitled to pick.

The measurement that decides it, and which neither C2 nor O5 performs, is
the full temporal autocorrelation as a function of the SENSOR-PIXEL
displacement vector, computed with no reference to the CFA at all, then
stratified by the CFA phase of the origin pixel.  Every number C2 and O5
report is one entry of that field, so the field either reproduces them --
which cross-validates two independent code paths -- or it does not.

DISCIPLINE 473 -- locate a mechanism by where the noise is generated.  A
correlation produced by charge diffusion or optical crosstalk MUST fall with
distance, because both are transport processes.  A correlation produced in a
shared readout node need not.  Distance is therefore the discriminator and
the field measures it directly.

CHECKS, each with its consequence, all declared before running:

  F1  SANITY.  The Delta = (0,0) entry must be 1.000000 to 6 decimals.
      If not, the estimator is wrong and nothing here is reported.

  F2  CROSS-VALIDATION, can fail.  Origin on G1, Delta = (+1,-1) reaches G2.
      That entry must equal 02-criteria's rho(G1,G2) for the same group to
      within 0.005, and origin on R with Delta = (+1,+1) must equal
      rho(R,B) to within 0.005.  These come from a different code path over
      a different pixel set, so agreement is evidence and disagreement kills
      the field, not the criteria.

  F3  DISTANCE.  Compare rho at |Delta| = 1 (nearest neighbour, always a
      different plane) against rho at |Delta| = sqrt(2) and |Delta| = 2.
      CONSEQUENCE: if rho at distance 1 is NOT the largest, no
      transport-based mechanism -- charge diffusion, optical crosstalk --
      can produce this field, and H6's signal-proportional crosstalk becomes
      less plausible as the explanation of the dark-frame structure.  This
      does not make dark frames able to see H6; it is a statement about the
      structure they can see.

  F4  THE ONE THAT CAN INVALIDATE MY OWN HEADLINE.  Compare rho(G1,G2) with
      the within-plane values at |Delta| = 2.
      CONSEQUENCE: if rho(G1,G2) is not larger than the within-plane
      |Delta| = 2 values by more than 0.010, then C2's GREEN-SPECIFIC
      verdict is REPORTED AS MISLEADING AS STATED: the greens are not
      distinguished by having a correlation, only by which control C2
      happened to compare them against.  I will say so in the report in
      those words, and the recommended model change follows the field, not
      C2.

  F5  ISO.  The field is measured at ISO 100 and ISO 1600 so the steep ISO
      dependence C5 found in rho(G1,G2) can be checked against the rest of
      the field.

Run: python 04-correlation-field.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("m72", HERE / "01-green-correlation.py")
m72 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m72)

CROP = 2400            # sensor pixels, even so the CFA phase is preserved
RAD = 4                # displacement window, sensor pixels
VAR_OUTLIER = 4.0      # exclude pixels whose temporal variance exceeds this
                       # multiple of the crop median -- the hot-pixel rule
GROUPS = [("118MSDCF", 100), ("121MSDCF", 1600)]

F1_TOL = 1e-6
F2_TOL = 0.005
F4_MARGIN = 0.010

PHASE_NAME = {(0, 0): "R", (0, 1): "G1", (1, 0): "G2", (1, 1): "B"}


def load_crop(folder: Path) -> np.ndarray:
    iso, frames = m72.load_group(folder)
    _, h, w = frames.shape
    r0 = ((h - CROP) // 2) & ~1
    c0 = ((w - CROP) // 2) & ~1
    return iso, frames[:, r0:r0 + CROP, c0:c0 + CROP].astype(np.float32)


def field_for(x: np.ndarray) -> dict:
    """Temporal correlation vs sensor-pixel displacement, by origin phase."""
    t = x.shape[0]
    x = x - x.mean(axis=0, keepdims=True)
    ss = np.einsum("tij,tij->ij", x, x)            # per-pixel sum of squares
    var = ss / (t - 1)
    med = float(np.median(var))
    good = var <= VAR_OUTLIER * med
    x *= good.astype(np.float32)
    ss = ss * good
    shep = (t - 1) / 12.0                          # Sheppard, per pixel

    lo, hi = RAD, CROP - RAD
    out: dict = {"median_var": med, "retained": float(good.mean()),
                 "grid": {}, "by_phase": {}}
    for dr in range(-RAD, RAD + 1):
        for dc in range(-RAD, RAD + 1):
            a = x[:, lo:hi, lo:hi]
            b = x[:, lo + dr:hi + dr, lo + dc:hi + dc]
            p = np.einsum("tij,tij->ij", a, b)
            sa = ss[lo:hi, lo:hi]
            sb = ss[lo + dr:hi + dr, lo + dc:hi + dc]
            ga = good[lo:hi, lo:hi]
            gb = good[lo + dr:hi + dr, lo + dc:hi + dc]
            gg = ga & gb
            for pr in (0, 1):
                for pc in (0, 1):
                    m = gg[pr::2, pc::2]
                    n = int(m.sum())
                    num = float(p[pr::2, pc::2][m].sum())
                    da = float(sa[pr::2, pc::2][m].sum()) - n * shep
                    db = float(sb[pr::2, pc::2][m].sum()) - n * shep
                    r = num / np.sqrt(da * db) if da > 0 and db > 0 else float("nan")
                    out["by_phase"].setdefault(PHASE_NAME[(pr, pc)], {})[f"{dr},{dc}"] = r
            # phase-agnostic, all origins pooled
            m = gg
            n = int(m.sum())
            num = float(p[m].sum())
            da = float(sa[m].sum()) - n * shep
            db = float(sb[m].sum()) - n * shep
            out["grid"][f"{dr},{dc}"] = num / np.sqrt(da * db) if da > 0 and db > 0 else float("nan")
    return out


def show_grid(g: dict, title: str) -> None:
    print(f"\n  {title}")
    print("      dc " + "".join(f"{dc:+9d}" for dc in range(-RAD, RAD + 1)))
    for dr in range(-RAD, RAD + 1):
        row = "".join(f"{g[f'{dr},{dc}']:+9.5f}" for dc in range(-RAD, RAD + 1))
        print(f"   dr {dr:+2d} {row}")


def main() -> int:
    crit = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    by_group = {r["group"]: r for r in crit["groups"]}
    fails = []
    results = {}

    for name, want_iso in GROUPS:
        iso, x = load_crop(m72.DARKS / name)
        if iso != want_iso:
            raise RuntimeError(f"{name}: ISO {iso}, expected {want_iso}")
        print("=" * 78)
        print(f"{name}  ISO {iso}   crop {CROP}x{CROP}   window +/-{RAD} sensor px")
        print("=" * 78)
        f = field_for(x)
        results[name] = f
        del x
        print(f"\n  median temporal var {f['median_var']:.5f} DN^2   "
              f"pixels retained {f['retained']:.5f}")
        show_grid(f["grid"], "rho vs sensor displacement, ALL origins pooled")
        for ph in ("R", "G1", "G2", "B"):
            show_grid(f["by_phase"][ph], f"origin phase {ph}")

        # ---- F1
        z = f["grid"]["0,0"]
        ok = abs(z - 1.0) <= F1_TOL
        print(f"\n  F1 Delta=(0,0) = {z:.8f}   {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"F1@{name}")

        # ---- F2
        pr = by_group[name]["arms"]["k6"]["pairs"]
        g1g2_field = f["by_phase"]["G1"]["1,-1"]
        rb_field = f["by_phase"]["R"]["1,1"]
        g1g2_crit = pr["G1-G2"]["rho_shep"]
        rb_crit = pr["R-B"]["rho_shep"]
        print(f"\n  F2 cross-validation against 02-criteria (independent path)")
        print(f"     G1->G2  field {g1g2_field:+.5f}  criteria {g1g2_crit:+.5f}  "
              f"diff {g1g2_field - g1g2_crit:+.5f}")
        print(f"     R ->B   field {rb_field:+.5f}  criteria {rb_crit:+.5f}  "
              f"diff {rb_field - rb_crit:+.5f}")
        ok = (abs(g1g2_field - g1g2_crit) <= F2_TOL and abs(rb_field - rb_crit) <= F2_TOL)
        print(f"     tol {F2_TOL}   {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"F2@{name}")

        # ---- F3
        d1 = np.mean([f["grid"]["0,1"], f["grid"]["1,0"],
                      f["grid"]["0,-1"], f["grid"]["-1,0"]])
        d2 = np.mean([f["grid"]["1,1"], f["grid"]["1,-1"],
                      f["grid"]["-1,1"], f["grid"]["-1,-1"]])
        d3 = np.mean([f["grid"]["0,2"], f["grid"]["2,0"],
                      f["grid"]["0,-2"], f["grid"]["-2,0"]])
        print(f"\n  F3 distance   |d|=1 {d1:+.5f}   |d|=sqrt2 {d2:+.5f}   |d|=2 {d3:+.5f}")
        if d1 >= max(d2, d3):
            print("     nearest neighbour is largest: consistent with a transport")
            print("     mechanism (charge diffusion / optical crosstalk).")
        else:
            print("     NEAREST NEIGHBOUR IS NOT LARGEST.  No transport mechanism")
            print("     can produce this field; the correlation is not carried by")
            print("     distance.  Consequence as declared.")

        # ---- F4
        within = [f["by_phase"]["G1"]["0,2"], f["by_phase"]["G1"]["2,0"],
                  f["by_phase"]["G2"]["0,2"], f["by_phase"]["G2"]["2,0"]]
        wmax = float(np.max(within))
        print(f"\n  F4 rho(G1,G2) {g1g2_field:+.5f} vs within-green |Delta|=2 "
              f"max {wmax:+.5f}")
        print(f"     margin {g1g2_field - wmax:+.5f}   required > {F4_MARGIN}")
        if g1g2_field - wmax > F4_MARGIN:
            print("     C2's GREEN-SPECIFIC verdict is supported by the field.")
        else:
            print("     C2's GREEN-SPECIFIC VERDICT IS MISLEADING AS STATED.")
            print("     The greens are not distinguished by having a correlation,")
            print("     only by which control C2 compared them against.  The")
            print("     recommended model change follows the field, not C2.")
            fails.append(f"F4@{name}")

    (DATA / "04-correlation-field.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    print("\n" + "=" * 78)
    print(f"checks that fired: {fails if fails else 'none'}")
    print("F4 firing is a RESULT, not an error: it qualifies C2.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
