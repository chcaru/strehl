"""Measure top-of-scale clipping in the masters BUILD-OUTPUT actually rendered.

ORCH broadcast an exposure regression at HEAD: `--srgb --auto-exposure` was
reported to blow 11 of 18 masters (>25% of pixels pinned at 65535, several with
a pure-white median), because a tone stage added since the acceptance pin
performs the same normalisation `--auto-exposure` performs, and `merge_cmd::run`
never received the guard `stack.rs:1644-1683` carries.

recert.py:69 pins FLAGS = "--srgb --auto-exposure", so every arm this lane
rendered is nominally in the blast radius. But this lane's binary is five
commits past f190a0ea and one of them is titled

    5f367a94 fix(exposure): stop --auto-exposure double-normalising the srgb render

so the arms may already carry the remedy. A commit subject is not a
measurement. This reads the emitted pixels.

Why the whole distribution and not just the clipped fraction: ORCH's
metrological point is that all four print-gate axes are structural and a
saturated region has no structure, so a blown master can read CLEAN on every
axis while being a white sheet. The diagnostic for that failure is the MEDIAN,
not the clipped count -- a master with 92% of pixels pinned has a pure-white
median, and a master with a sane median cannot be a white sheet whatever its
tail does. Both are printed, and the verdict conditions on both.

Reported per file:
  clip_frac  fraction of channel samples at exactly 65535 (the pin)
  near_frac  fraction at >= 65500 (the gate's old one-sided test)
  median     median channel sample; 65535 means "pure white median"
  p99.9      the top of the real distribution, to separate genuine speculars
             (a thin tail) from a normalisation blowout (a fat one)

Thresholds are ORCH's, quoted so this file is readable without his message:
BLOWN at clip_frac > 0.25; his clean masters read 0.00-0.09%.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile

BLOWN = 0.25
# ORCH's delivered SHIP-V4 masters, which he verified are unaffected (rendered
# by the pin), read 0.0000-0.0009. Anything at or below that is indistinguishable
# from the known-good population.
CLEAN = 0.0009

ARMS = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\arms")
SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
SUBJECTS = ["coffee-bubbles", "lead-1-cpl", "113MSDCF",
            "flat-on-ruler-cpl", "112MSDCF", "foam"]


def probe(path):
    a = tifffile.imread(str(path))
    if a.dtype != np.uint16:
        raise SystemExit(f"{path}: expected uint16, got {a.dtype}")
    flat = a.reshape(-1)
    n = flat.size
    return {
        "clip_frac": float(np.count_nonzero(flat == 65535)) / n,
        "near_frac": float(np.count_nonzero(flat >= 65500)) / n,
        "median": int(np.median(flat)),
        "p999": int(np.percentile(flat, 99.9)),
        "shape": list(a.shape),
    }


def find(arm_dir, subject):
    hits = sorted(arm_dir.glob(f"{subject}--*.tiff"))
    return hits[0] if hits else None


def main():
    arms = sys.argv[1:] or ["SC-BASE-bc6fa3c7", "SC-D4096-bc6fa3c7"]
    out = {}
    rows = []
    for arm in arms:
        d = ARMS / arm
        if not d.is_dir():
            raise SystemExit(f"missing arm dir {d}")
        out[arm] = {}
        for s in SUBJECTS:
            p = find(d, s)
            if p is None:
                rows.append((arm, s, None))
                continue
            r = probe(p)
            out[arm][s] = r
            rows.append((arm, s, r))

    # The delivered pin masters, as the known-good control population. Without
    # these the numbers above have no scale: "0.0003 clipped" only means
    # something against what a master ORCH has certified unaffected reads.
    out["SHIP-V4"] = {}
    for s in SUBJECTS:
        p = find(SHIP, s)
        if p is None:
            continue
        r = probe(p)
        out["SHIP-V4"][s] = r
        rows.append(("SHIP-V4", s, r))

    w = f"{'arm':<20} {'subject':<20} {'clip%':>9} {'near%':>9} {'median':>8} {'p99.9':>8}  verdict"
    print(w)
    print("-" * len(w))
    worst = 0.0
    for arm, s, r in rows:
        if r is None:
            print(f"{arm:<20} {s:<20} {'MISSING':>9}")
            continue
        if r["clip_frac"] > BLOWN:
            v = "BLOWN"
        elif r["clip_frac"] > CLEAN:
            v = "ELEVATED"
        else:
            v = "clean"
        if r["median"] == 65535:
            v += " WHITE-MEDIAN"
        if arm != "SHIP-V4":
            worst = max(worst, r["clip_frac"])
        print(f"{arm:<20} {s:<20} {100*r['clip_frac']:9.4f} {100*r['near_frac']:9.4f} "
              f"{r['median']:8d} {r['p999']:8d}  {v}")

    dst = Path(__file__).with_name("clipprobe.json")
    dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print()
    print(f"worst clip_frac across this lane's arms: {100*worst:.4f}%  "
          f"(BLOWN threshold {100*BLOWN:.0f}%)")
    # A printed number must be conditioned on (AGENTS.md). This is that condition.
    if worst > BLOWN:
        print("VERDICT: this lane's evidence base is BLOWN and must be re-rendered.")
        return 1
    if worst > CLEAN:
        print("VERDICT: ELEVATED above the delivered population; inspect before relying.")
        return 2
    print("VERDICT: this lane's arms are within the delivered masters' clipping "
          "population. Evidence base stands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
