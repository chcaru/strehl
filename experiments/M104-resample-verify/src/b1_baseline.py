"""M104 B1 -- the PRE-FIX baseline.  Frozen before M95's change lands.

Measured at HEAD 6a8ac30, with merge_cmd.rs:1246 still reading "then upsampled
to keep the output dimensions" -- verified before rendering, so these are
genuine before numbers and not a reconstruction.

WHAT IS MEASURED, AND WHY EACH IS THE RIGHT QUANTITY

  mag = f0_A0 / f0_ALN
        The magnification of the registered render relative to the
        unregistered one, read from the tick comb.  Pre-fix this should equal
        1/k, the reciprocal of the coverage scale the aligner itself declares
        in the render log.  Recovering the log's own number from a photograph
        is the cross-check; it is not an input.

  extent = width_px * f0                                     [B5, H3]
        Field of view in TICKS -- a physical unit.  This is the invariant that
        separates the two things that could produce a smaller output: removing
        the upsample (sampling changes, extent does NOT), or cropping harder
        (extent changes).  Those are different operations and only the first
        is the fix.  B1 passing while B5 fails is a FAIL even if the picture
        looks better, and that was registered in advance.

  mod_ratio = Mn(ALN) / Mn(A0)                               [B4, H2]
        Modulation depth at the comb, each arm probed at ITS OWN f0 -- so both
        are probed at the same OBJECT frequency however they are sampled.
        Normalised by ROI mean level, which is the defect M98's S8 had and
        refused to draw a conclusion from.

  D_hi = log10( P_hi(A0) / P_hi(ALN) )                       [B6, H4]
        Contrast-normalised annulus power over [1.5*f0, 2.5*f0] in each arm's
        OWN units, hence the same object band in both.  Positive means the
        registered render has less high-frequency detail than the unregistered
        one.  Reported in dex to be commensurable with the orchestrator's
        independent spectral measurement (facts 1286, 1287) without sharing
        any code with it.

RULE 18.  Removing an upsample makes the render smaller in pixels, so every
per-pixel metric improves for free.  That bias runs toward "the fix worked".
Every number above is object-space; the pixel-space band ratio is printed too,
labelled DIAGNOSTIC, and no bar depends on it.

bee-3-cpl carries no comb, so it supplies dimensions and the aligner's declared
k only.  Its object-space numbers are not measurable with this instrument and
are not claimed.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m104lib as L

OUT = Path(__file__).resolve().parent.parent / "out"
PHASE = sys.argv[1] if len(sys.argv) > 1 else "PRE"
COLS, ROWS = 8, 6
STACKS = ["flat-on-ruler-cpl", "bee-3-cpl"]

log = []


def say(s=""):
    print(s)
    log.append(s)


def declared_k(stack: str) -> float:
    p = Path(L.LOGS) / f"{stack}-{PHASE}-ALN-g0.log"
    if not p.exists():
        return float("nan")
    m = re.search(r"field of view scaled to ([0-9.]+)",
                  p.read_text(encoding="utf-8", errors="replace"))
    return float(m.group(1)) if m else float("nan")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    L.ROI = 384
    res = {"phase": PHASE, "stacks": {}}

    say("=" * 78)
    say(f"M104 B1 -- {PHASE}-FIX baseline")
    say("  reference arm : STREHL_ALIGN=0, gate 0  (no warp, no rescale,")
    say("                  native sampling, strehl's own decoder)")
    say("  test arm      : alignment ON, gate 0")
    say("  gate 0 takes one frame per pixel, so the ONLY difference between")
    say("  the arms is the warp and the coverage rescale.")
    say("=" * 78)
    say()

    for stack in STACKS:
        a0 = Path(L.RENDERS) / f"{stack}-{PHASE}-A0-g0.tif"
        al = Path(L.RENDERS) / f"{stack}-{PHASE}-ALN-g0.tif"
        if not (a0.exists() and al.exists()):
            say(f"MISSING renders for {stack}")
            continue
        A = L.green(a0)
        B = L.green(al)
        k = declared_k(stack)
        say("-" * 78)
        say(f"{stack}")
        say(f"  A0  {A.shape[1]} x {A.shape[0]}      ALN {B.shape[1]} x {B.shape[0]}")
        say(f"  aligner declares k = {k:.4f}  ->  predicted mag = 1/k = {1/k:.6f}")
        d = dict(dims_a0=[A.shape[1], A.shape[0]], dims_aln=[B.shape[1], B.shape[0]],
                 k=k, mag_pred=1 / k)

        seed = L.seed_combs(A, cols=COLS, rows=ROWS)
        if len(seed) < 8:
            say(f"  no usable comb ({len(seed)} seeded ROIs) -- "
                f"object-space metrics NOT measurable on this subject.")
            say("  dimensions and declared k recorded; no object-space claim made.")
            res["stacks"][stack] = d
            say()
            continue

        rows = L.measure_pair(A, B, seed, COLS, ROWS)
        mag, mag_se, n = L.gmean_se([r["mag"] for r in rows])
        sig = abs(mag - d["mag_pred"]) / mag_se if mag_se > 0 else float("nan")
        say(f"  live ROIs                 : {n} of {COLS*ROWS}")
        say(f"  mag = f0(A0)/f0(ALN)      : {mag:.6f} +/- {mag_se:.6f}")
        say(f"  vs aligner's own 1/k      : {d['mag_pred']:.6f}   "
            f"({sig:.2f} sigma)")

        ext_a0 = [A.shape[1] * r["f0_ref"] for r in rows]
        ext_al = [B.shape[1] * r["f0_test"] for r in rows]
        er, er_se, _ = L.gmean_se([b / a for a, b in zip(ext_a0, ext_al)])
        say(f"  extent ALN / extent A0    : {er:.6f} +/- {er_se:.6f}   "
            f"(ticks across frame; expect ~k = {k:.4f})")

        mr, mr_se, _ = L.gmean_se([r["mod_ratio"] for r in rows])
        say(f"  object-space modulation   : {mr:.6f} +/- {mr_se:.6f}   "
            f"({(mr-1)*100:+.2f}%)")

        dh = [r["d_hi"] for r in rows if np.isfinite(r["d_hi"])]
        dhm = float(np.mean(dh))
        dhse = float(np.std(dh, ddof=1) / np.sqrt(len(dh)))
        f0med = float(np.median([r["f0_ref"] for r in rows]))
        say(f"  comb f0 (median, A0)      : {f0med:.5f} cyc/px  -> object band "
            f"[{L.HI_LO*f0med:.4f}, {L.HI_HI*f0med:.4f}] cyc/px")
        say(f"  D_hi (comb band, dex)     : {dhm:+.4f} +/- {dhse:.4f}   "
            f"(+ve = ALN has less detail)")
        say(f"                              power ratio {10**dhm:.4f}x")

        dn = [r["d_nyq_star"] for r in rows if np.isfinite(r["d_nyq_star"])]
        dnm = float(np.mean(dn))
        dnse = float(np.std(dn, ddof=1) / np.sqrt(len(dn)))
        say(f"  D_nyq [{L.NYQ_LO}, {L.NYQ_HI}] cyc/px, object-corrected, Jacobian-corrected (D_nyq*)")
        say(f"                            : {dnm:+.4f} +/- {dnse:.4f} dex   "
            f"({dnm/dnse if dnse>0 else float('nan'):.2f} sigma)")
        say(f"                              power ratio {10**dnm:.4f}x")

        d.update(n=n, mag=mag, mag_se=mag_se, mag_sigma=sig,
                 extent_ratio=er, extent_se=er_se,
                 mod_ratio=mr, mod_se=mr_se, f0_med=f0med,
                 d_hi=dhm, d_hi_se=dhse, d_nyq_star=dnm, d_nyq_se=dnse,
                 rois=[{k2: v2 for k2, v2 in r.items() if k2 != "P"}
                       for r in rows])
        res["stacks"][stack] = d
        say()

    say("=" * 78)
    say(f"{PHASE}-fix baseline frozen.")
    say("=" * 78)

    (OUT / f"b1_baseline_{PHASE}.json").write_text(
        json.dumps(res, indent=1), encoding="utf-8")
    (OUT / f"b1_baseline_{PHASE}.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
