"""Both ends of the tone scale, SHIP-V4 against a candidate arm, per subject.

WHY THIS EXISTS, SEPARATELY FROM THE BAND GAUGE
-----------------------------------------------
The band gauge in ``recertlib.py`` measures noise and sharpness, and it is the
right instrument for "is the merge better". It is the wrong instrument for the
failure this script found: a tone-scale change large enough to destroy detail by
saturation does not read as noise, and can read as *less* noise, because a region
pinned at 65535 has zero variance. An image driven to white is, to a noise
statistic, immaculate.

So this is measured on its own axis and gated on its own terms.

BOTH ENDS, DELIBERATELY
-----------------------
AGENTS.md records that ``orch_printready.py`` once tested ``>= 65500`` only and
certified 15 masters print-ready while blind to the end where this corpus
actually clips. A clipping gate that tests one end of the tone scale has tested
half the tone scale. This reports the top (>= 65500) and the bottom (<= 35) for
every subject and every arm, and both participate in the verdict.

THE COMPARISON IS RELATIVE, NOT ABSOLUTE
----------------------------------------
AGENTS.md: a statistic earns an absolute threshold only if it has been
commissioned to be subject-invariant. Clipping is emphatically not -- a subject
with a genuine specular highlight legitimately clips where a diffuse one does
not, which is a property of the scene and not of the merge. Every verdict here
is therefore SHIP-V4 against the candidate on the *same subject*, and the
threshold is a movement, not a level.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

SHIP = Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")

TOP = 65500      # at or above this is a blown highlight
BOT = 35         # at or below this is a crushed shadow

# A movement smaller than this is not worth a sentence. Chosen as 10x the
# largest top-end value in the SHIP-V4 corpus norm quoted by ORCH (0.02%), so a
# subject has to move well outside the corpus's own spread to be named.
MOVE_PCT = 0.20


def tone(path):
    """Top-end, bottom-end and level statistics for one master.

    Returns percentages of *samples* (not pixels) at each end, plus the
    any-channel pixel fraction at the top, because a pixel with one channel
    blown has lost its colour even though two channels survived.
    """
    a = tifffile.imread(path)
    n = a.size
    px = a.shape[0] * a.shape[1]
    return {
        "clip_pct": 100.0 * np.count_nonzero(a >= TOP) / n,
        "clip_px_pct": 100.0 * np.count_nonzero((a >= TOP).any(axis=2)) / px,
        "crush_pct": 100.0 * np.count_nonzero(a <= BOT) / n,
        "mean": float(a.mean()),
        "p99_9": float(np.percentile(a, 99.9)),
    }


def commission():
    """Three arms: clean, planted defect, planted improvement.

    A suite that plants only degradations cannot tell a metric that is *blind*
    to a defect from one that is *perverse* on it. This project has shipped
    exactly that bug, so the improvement arm is mandatory and its absence would
    make the other two worthless.
    """
    print("=== commissioning the tone census ===")
    ok = True
    rng = np.random.default_rng(7)
    h = w = 512
    n = h * w * 3
    tmp = Path(__file__).parent / "_commission_tone.tiff"

    # A1 KNOWN-CLEAN: nothing near either rail. Must read exactly zero at both
    # ends. A census that manufactures clipping would fail here.
    clean = rng.integers(8000, 40000, size=(h, w, 3), dtype=np.uint16)
    tifffile.imwrite(tmp, clean)
    t = tone(tmp)
    a1 = t["clip_pct"] == 0.0 and t["crush_pct"] == 0.0
    print(f"  A1 clean input          -> clip {t['clip_pct']:.4f}%  crush {t['crush_pct']:.4f}%"
          f"   {'PASS' if a1 else 'FAIL'}")
    ok &= a1

    # A2 PLANTED DEFECT, WITH A KNOWN COUNT: not merely "detects something", but
    # recovers the exact fraction. A detector that fires on any clipping tells
    # you less than one whose number you can predict in advance.
    k_top, k_bot = 1234, 567
    d = clean.copy().reshape(-1)
    idx = rng.choice(n, size=k_top + k_bot, replace=False)
    d[idx[:k_top]] = 65535
    d[idx[k_top:]] = 0
    tifffile.imwrite(tmp, d.reshape(h, w, 3))
    t = tone(tmp)
    exp_top, exp_bot = 100.0 * k_top / n, 100.0 * k_bot / n
    a2 = (abs(t["clip_pct"] - exp_top) < 1e-9) and (abs(t["crush_pct"] - exp_bot) < 1e-9)
    print(f"  A2 planted {k_top} top / {k_bot} bottom -> clip {t['clip_pct']:.5f}% "
          f"(expect {exp_top:.5f})  crush {t['crush_pct']:.5f}% (expect {exp_bot:.5f})"
          f"   {'PASS' if a2 else 'FAIL'}")
    ok &= a2

    # A3 PLANTED IMPROVEMENT: take a genuinely clipped image and pull the
    # exposure down. The clipping must FALL. A statistic bounded below by zero
    # that can only ever charge for a defect would pass A1 and A2 and still be
    # incapable of scoring a repair -- which is precisely the shape of bug this
    # project has already shipped once.
    blown = np.clip(clean.astype(np.float64) * 2.445, 0, 65535).astype(np.uint16)
    tifffile.imwrite(tmp, blown)
    before = tone(tmp)["clip_pct"]
    fixed = np.clip(clean.astype(np.float64) * 1.20, 0, 65535).astype(np.uint16)
    tifffile.imwrite(tmp, fixed)
    after = tone(tmp)["clip_pct"]
    a3 = before > 0.0 and after < before
    print(f"  A3 planted improvement  -> clip {before:.4f}% -> {after:.4f}%  (must fall)"
          f"   {'PASS' if a3 else 'FAIL'}")
    ok &= a3

    tmp.unlink(missing_ok=True)
    print(f"  commissioning {'PASSED' if ok else 'FAILED'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="directory of candidate masters")
    ap.add_argument("--label", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()

    if not commission():
        print("REFUSING: the census failed its own commissioning; its numbers mean nothing.")
        return 2
    if a.commission:
        return 0

    arm = Path(a.arm)
    label = a.label or arm.name
    ship = {p.name.split("--")[0]: p for p in SHIP.glob("*.tiff")}
    cand = {p.name.split("--")[0]: p for p in arm.glob("*.tiff")}

    rows, worse, better, held = [], [], [], []
    for s in sorted(ship):
        if s not in cand:
            continue
        b, c = tone(ship[s]), tone(cand[s])
        d_clip = c["clip_pct"] - b["clip_pct"]
        d_crush = c["crush_pct"] - b["crush_pct"]
        ratio = c["mean"] / b["mean"] if b["mean"] else float("nan")
        rows.append({"subject": s, "ship": b, "cand": c,
                     "d_clip": d_clip, "d_crush": d_crush, "mean_ratio": ratio})
        if d_clip > MOVE_PCT or d_crush > MOVE_PCT:
            worse.append(s)
        elif d_clip < -MOVE_PCT or d_crush < -MOVE_PCT:
            better.append(s)
        else:
            held.append(s)

    print(f"\n=== tone census: SHIP-V4 vs {label} ===")
    print(f"{'subject':34s} {'clip SHIP':>10s} {'clip CAND':>10s} {'d':>9s} "
          f"{'crush SHIP':>11s} {'crush CAND':>11s} {'mean x':>7s}")
    for r in rows:
        flag = "  WORSE" if r["subject"] in worse else ("  better" if r["subject"] in better else "")
        print(f"{r['subject']:34s} {r['ship']['clip_pct']:9.4f}% {r['cand']['clip_pct']:9.4f}% "
              f"{r['d_clip']:+9.4f} {r['ship']['crush_pct']:10.4f}% {r['cand']['crush_pct']:10.4f}% "
              f"{r['mean_ratio']:7.3f}{flag}")

    missing = len(ship) - len(rows)
    print(f"\n  compared {len(rows)}   not yet rendered {missing}   "
          f"total {len(rows) + missing} of {len(ship)}")
    print(f"  WORSE {len(worse)}   better {len(better)}   held {len(held)}"
          f"   (partition sums to {len(worse) + len(better) + len(held)} = {len(rows)})")

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"label": label, "rows": rows, "worse": worse,
             "better": better, "held": held, "missing": missing}, indent=1), encoding="utf-8")

    # A value printed but never conditioned on is a defect.
    if missing:
        print("\nINCONCLUSIVE: the arm is incomplete; this is a partial census.")
        return 1
    if worse:
        print(f"\nVERDICT: TONE REGRESSION on {len(worse)} subject(s): {', '.join(worse)}")
        return 1
    print("\nVERDICT: tone held on every subject.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
