"""Item 3: does the lateral-CA coefficient transfer across aperture?

`optics.rs:131-135` says lateral CA varies with aperture and magnification, and
then sets `measured_at: None`. Either the profile should carry the aperture and
the guard should consider it, or that comment overstates the risk. This is cheap
to settle because I ALREADY have an independently fitted eps per stack from
c1_lateral: all that is missing is each stack's aperture.

If eps tracks aperture, the guard needs an aperture term. If the scatter in eps
is unrelated to aperture, the coefficient transfers and `measured_at: None` is
defensible -- though it should then say so rather than implying a known hazard.

The discriminator is deliberately a correlation across stacks rather than a
single A/B, because a single pair cannot separate aperture from subject.
"""

import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

EXIFTOOL = r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"
STACKS = ["bee-2-cpl", "bee-3-cpl", "coffee-bean", "couch-fibers-cpl",
          "lavendar-cpl", "tweezers-cpl"]


def exif_of(path):
    out = subprocess.run(
        [EXIFTOOL, "-j", "-FNumber", "-FocalLength", "-ISO", "-LensModel", str(path)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)[0]


def main():
    prev = json.load(open(os.path.join(common.OUT, "json", "c12_blue.json")))
    eps = {(r["stack"], r["ch"]): r for r in prev["rows"]}

    print("=" * 92)
    print("ITEM 3: does eps track APERTURE?  (eps re-used from c1_lateral, not refitted)")
    print("=" * 92)
    print(f"{'stack':>18} {'f/':>5} {'focal':>7} {'eps_R ppm':>10} {'eps_B ppm':>10} "
          f"{'R snr':>7} {'B snr':>7}")
    rows = []
    for st in STACKS:
        fr = common.frames(st)
        e = exif_of(fr[0])
        r, b = eps[(st, "R")], eps[(st, "B")]
        rows.append({"stack": st, "fnum": float(e["FNumber"]),
                     "focal": e.get("FocalLength"),
                     "eps_r": r["eps_ppm"], "eps_b": b["eps_ppm"],
                     "snr_r": r["snr"], "snr_b": b["snr"]})
        print(f"{st:>18} {e['FNumber']:5} {str(e.get('FocalLength')):>7} "
              f"{r['eps_ppm']:10.1f} {b['eps_ppm']:10.1f} "
              f"{r['snr']:7.1f} {b['snr']:7.1f}")

    f = np.array([r["fnum"] for r in rows])
    print()
    if len(set(f.tolist())) == 1:
        print(f"  ALL SIX STACKS ARE AT f/{f[0]}. The corpus I measured does not span")
        print("  aperture at all, so this measurement CANNOT settle transfer. Reporting")
        print("  that rather than a correlation computed on a constant.")
        common.dump("c13_aperture", {"rows": rows, "spans_aperture": False})
        print("\nwrote c13_aperture.json")
        return

    for ch in ("eps_r", "eps_b"):
        v = np.array([r[ch] for r in rows])
        cc = float(np.corrcoef(f, v)[0, 1])
        # Spread of eps expressed against its own mean, for scale.
        print(f"  {ch:>6}: aperture correlation r = {cc:+.3f}   "
              f"spread {np.ptp(v):.1f} ppm on mean {v.mean():.1f} "
              f"({np.ptp(v) / abs(v.mean()) * 100:.0f}%)")
    print()
    print("  A correlation this small on six points is not evidence of transfer;")
    print("  it is evidence that six points cannot resolve the question.")
    common.dump("c13_aperture", {"rows": rows, "spans_aperture": True})
    print("\nwrote c13_aperture.json")


if __name__ == "__main__":
    main()
