"""Corpus-verify eps_r = -508.4 ppm against -704.5 ppm and against CA off.

Per ORCH fact 1886, absolutes expire and only ORDERING is stable, so this
reports an ordering per subject and counts wins/losses. Every arm of every
subject comes from ONE of two PINNED binaries whose SHA256 is recorded and
re-checked at the end.

Statistic: ORCH's hue-neutral chroma magnitude, imported from
`orch_chromamag.py` rather than reimplemented, so the two cannot drift. Edge and
flat populations are derived from the SHIPPED arm and applied to all three, so
the three arms are scored on identical pixels.

PROXY, stated plainly: these are SINGLE-FRAME renders, not 299-frame masters.
Validated on `dry-erase-marker-head-cpl`, where the master ordering is
off 0.15576 > shipped 0.11377 > refit 0.10093 and the single-frame ordering is
the same, with a compressed effect size (-2.0% vs -11.3%). The proxy is
therefore CONSERVATIVE on magnitude and faithful on sign. It removes the merge
and its frame election, which is what confounded the green question.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ORCH-drift-check"))
from orch_chromamag import load, populations, score  # noqa: E402

ARMS = ("shipped", "refit", "off")


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:\strehl-out\BUILD-CROP\sfout"
    names = sorted({f.split(".")[0] for f in os.listdir(outdir)
                    if f.endswith(".tiff")})
    print(f"{'subject':<38} {'shipped':>9} {'refit':>9} {'off':>9} "
          f"{'refit-vs-ship':>14} {'verdict':>9}")
    print("-" * 92)
    rows = []
    for name in names:
        paths = {a: os.path.join(outdir, f"{name}.{a}.tiff") for a in ARMS}
        if not all(os.path.exists(p) for p in paths.values()):
            print(f"{name:<38} {'INCOMPLETE -- UNSCORED':>50}")
            continue
        try:
            imgs = {a: load(paths[a]) for a in ARMS}
        except Exception as exc:
            print(f"{name:<38} UNSCORED (load failed: {exc})")
            continue
        # populations from the SHIPPED arm, applied to all three
        edge, flat = populations(imgs["shipped"])
        if int(edge.sum()) < 10000:
            print(f"{name:<38} UNSCORED (only {int(edge.sum())} edge px)")
            continue
        s = {a: score(imgs[a], edge, flat) for a in ARMS}
        em = {a: s[a]["edge_mean"] for a in ARMS}
        delta = 100.0 * (em["refit"] - em["shipped"]) / em["shipped"]
        verdict = "WIN" if delta < 0 else ("LOSS" if delta > 0 else "TIE")
        print(f"{name:<38} {em['shipped']:9.5f} {em['refit']:9.5f} "
              f"{em['off']:9.5f} {delta:+13.2f}% {verdict:>9}")
        rows.append((name, em["shipped"], em["refit"], em["off"], delta, verdict))

    if not rows:
        print("\nno subjects scored")
        return 1
    print()
    w = sum(1 for r in rows if r[5] == "WIN")
    l = sum(1 for r in rows if r[5] == "LOSS")
    print(f"ORDERING: re-fit beats shipped on {w} of {len(rows)} scored, "
          f"loses on {l}")
    ob = sum(1 for r in rows if r[2] < r[3])
    print(f"          re-fit beats CA-off  on {ob} of {len(rows)} scored")
    sb = sum(1 for r in rows if r[1] < r[3])
    print(f"          shipped beats CA-off on {sb} of {len(rows)} scored")
    d = np.array([r[4] for r in rows])
    print(f"          refit-vs-shipped delta: median {np.median(d):+.2f}%  "
          f"range {d.min():+.2f}% .. {d.max():+.2f}%")
    print("\nLOSSES (if any) -- these are the subjects that matter:")
    any_loss = False
    for r in rows:
        if r[5] == "LOSS":
            any_loss = True
            print(f"  {r[0]:<38} shipped {r[1]:.5f} -> refit {r[2]:.5f} "
                  f"({r[4]:+.2f}%)")
    if not any_loss:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
