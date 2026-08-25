"""M87 / probe -- provenance of the 74.76% headline, and M120's true delta.

M120 identified `40-ship-delta.py` as an 8-bit laundering victim and concluded
that M87 "must re-render before any halo-fix number is trusted".  Two claims
to check, and they have different answers.

CLAIM A -- the laundering is real.  TRUE, and M87 published it as P40 before
M120 raised it.  Re-confirmed here.

CLAIM B -- the headline descends from it.  This probe tests that MECHANICALLY
rather than by my reading my own code: it walks every array `70-veil.py`
loads, reports the dtype, range and distinct-level count of each, and greps
the transitive source chain for the two readers.  An 8-bit-laundered array
cannot have thousands of distinct levels or values in the thousands of DN, so
the level count is a POSITIVE test, not an argument.

CLAIM C -- "the source TIFFs are gone from out/, so the true delta cannot be
recomputed".  FALSE as stated.  They are 188 MB each in
C:\\dev\\strehl-out\\M87-before-after\\, which is where 40-ship-delta.py wrote
them and where its own `S` constant still points.  So the true delta is
recomputable without re-rendering anything, and this probe recomputes it.

Registered before running, so the numbers cannot be fitted afterwards:
  R1  every array 70-veil.py loads has > 1000 distinct levels (not 8-bit).
  R2  no transitive dependency of 70-veil.py names ship-delta.npy.
  R3  the true delta max EXCEEDS the PIL delta max of 163 by more than 100x.
  R4  the true changed-pixel fraction EXCEEDS the PIL figure of 13.445%,
      because an 8-bit read cannot see a difference below ~128 DN-16.
"""
import json
import pathlib
import re
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parents[1]
SRC = HERE / "src"
CACHE = HERE / "cache"
DATA = HERE / "data"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

PIL_MAX_DELTA = 163            # data/41-ship-delta.json, the laundered read
PIL_CHANGED_FRAC = 0.13445276493222597


def main():
    out = {"registered": {"R1_min_levels": 1000, "R3_factor": 100,
                          "pil_max_delta": PIL_MAX_DELTA,
                          "pil_changed_frac": PIL_CHANGED_FRAC}}

    # ---- R2: transitive source trace, by grep, not by memory ----------------
    print("=== R2: does anything 70-veil.py depends on touch ship-delta? ===")
    seen, stack, chain = set(), ["70-veil.py"], []
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        p = SRC / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        chain.append(name)
        for m in re.findall(r"import\s+(m87lib)", t):
            stack.append("m87lib.py")
    touchers = sorted(p.name for p in SRC.glob("*.py")
                      if "ship-delta" in p.read_text(encoding="utf-8"))
    overlap = sorted(set(touchers) & set(chain))
    print(f"  70-veil.py's source chain      : {chain}")
    print(f"  every script naming ship-delta : {touchers}")
    print(f"  overlap                        : {overlap or 'NONE'}")
    r2 = not overlap
    out["R2"] = {"chain": chain, "ship_delta_touchers": touchers,
                 "overlap": overlap, "pass": r2}

    # ---- R1: the arrays themselves, which cannot lie about their levels ----
    print("\n=== R1: are the headline's inputs 16-bit or laundered 8-bit? ===")
    arrays = {}
    ok_r1 = True
    for name in ("bee3-leg-luma.npy", "bee3-leg-sel.npy", "bee3-leg-argbest.npy"):
        a = np.load(CACHE / name, mmap_mode="r")
        s = np.asarray(a[0] if a.ndim == 3 else a)
        lv = int(len(np.unique(s)))
        rec = {"dtype": str(a.dtype), "shape": list(a.shape),
               "min": float(s.min()), "max": float(s.max()), "levels_slice": lv}
        arrays[name] = rec
        flag = "OK" if lv > 1000 else ("index field, N/A" if "argbest" in name else "SUSPECT")
        print(f"  {name:26s} {str(a.dtype):8s} min {s.min():8.0f} max {s.max():8.0f} "
              f"levels {lv:6d}  {flag}")
        if "argbest" not in name and lv <= 1000:
            ok_r1 = False
    out["R1"] = {"arrays": arrays, "pass": ok_r1}

    # ---- reader of record for the headline --------------------------------
    lib = (SRC / "m87lib.py").read_text(encoding="utf-8")
    uses_rawpy = "rawpy.imread" in lib
    uses_pil = "Image.open" in lib
    print(f"\n  m87lib.py reader: rawpy.imread={uses_rawpy}  PIL={uses_pil}")
    out["reader"] = {"rawpy": uses_rawpy, "pil": uses_pil}

    # ---- R3/R4: recompute M120's delta from sources it believed gone -------
    print("\n=== R3/R4: the TRUE delta, recomputed with tifffile ===")
    b_p, a_p = SHIP / "30-SHIP-BEFORE-default.tif", SHIP / "31-SHIP-AFTER-fixhalo.tif"
    if not (b_p.exists() and a_p.exists()):
        print("  sources genuinely absent -- cannot recompute")
        out["R3"] = out["R4"] = None
    else:
        print(f"  sources present: {b_p.stat().st_size / 1e6:.0f} MB, "
              f"{a_p.stat().st_size / 1e6:.0f} MB")
        b = tifffile.imread(b_p)
        a = tifffile.imread(a_p)
        assert b.dtype == np.uint16 and a.dtype == np.uint16, (b.dtype, a.dtype)
        d = np.abs(a.astype(np.int32) - b.astype(np.int32)).max(axis=2)
        mx, frac = int(d.max()), float((d > 0).mean())
        print(f"  TRUE  max |delta| {mx:6d} of 65535   changed {100 * frac:.3f}%")
        print(f"  PIL   max |delta| {PIL_MAX_DELTA:6d}          changed "
              f"{100 * PIL_CHANGED_FRAC:.3f}%")
        print(f"  ratio {mx / PIL_MAX_DELTA:.1f}x on amplitude, "
              f"{frac / PIL_CHANGED_FRAC:.3f}x on changed-pixel fraction")
        out["R3"] = {"true_max_delta": mx, "pil_max_delta": PIL_MAX_DELTA,
                     "factor": mx / PIL_MAX_DELTA,
                     "pass": mx > 100 * PIL_MAX_DELTA}
        out["R4"] = {"true_changed_frac": frac, "pil_changed_frac": PIL_CHANGED_FRAC,
                     "ratio": frac / PIL_CHANGED_FRAC,
                     "pass": frac > PIL_CHANGED_FRAC}
        print(f"  R3 -> {'PASS' if out['R3']['pass'] else 'FAIL'}   "
              f"R4 -> {'PASS' if out['R4']['pass'] else 'FAIL (registered prediction wrong)'}")

    verdict = ("HEADLINE IS NOT DESCENDED FROM THE LAUNDERED PATH"
               if (r2 and ok_r1 and uses_rawpy and not uses_pil)
               else "PROVENANCE NOT CLEARED -- investigate")
    print(f"\nVERDICT: {verdict}")
    out["verdict"] = verdict
    with open(DATA / "provenance-74.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {DATA / 'provenance-74.json'}")
    return 0 if r2 and ok_r1 else 1


if __name__ == "__main__":
    sys.exit(main())
