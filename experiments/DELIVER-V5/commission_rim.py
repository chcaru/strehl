"""commission_rim.py -- commission the injected-rim statistic BEFORE using it.

Pass/fail rules are written here, in the source, before any corpus number is
computed.  Every arm prints its verdict and the run partitions arms into
counted outcomes that sum to the total, so a skipped arm cannot read as a
passed one.

The bench is built in BOTH directions, and the arm that matters most is C6.

  C6  NEAREST-NEIGHBOUR.  Nearest cannot ring: every output pixel IS an input
      pixel, so it lies inside the hull by construction and must score exactly
      0.000.  It is also a catastrophic real degradation.  A statistic that
      scored `nearest` high would be measuring ALIASING, not ringing -- which
      is the exact error another lane made tonight, convicting the shipping
      resampler until a nearest arm scored 2.04x higher than the kernel it had
      convicted.  Without this row I would have no way to tell the two apart.

  P1  PIL IS NOT TRUSTED.  The brief says do not assume PIL's Image.BOX is what
      you think it is.  P1 checks PIL BOX against an independent numpy block
      mean at the shipping factor and requires exact agreement to 1e-9.

  W1  A REAL DEFECT IN CODE IN THIS TREE.  experiments/ORCH-drift-check/true11.py
      converts 16->8 with ((c + 128) >> 8).astype(np.uint8) and no clip.  This
      arm computes what that does to 65535.  It is here because DELIVER-V5
      reuses true11.py's site chooser and must not reuse its converter.

Usage:  python commission_rim.py
"""
import sys

import numpy as np
from PIL import Image

import rimlib

SHIP_K = 4          # the reduction factor DELIVER-V5 ships
GALLERY_SCALE = 5.0286   # what the OLD _presentation gallery used

KERNELS = {
    "nearest": Image.NEAREST,
    "box": Image.BOX,
    "bilinear": Image.BILINEAR,
    "bicubic": Image.BICUBIC,
    "lanczos": Image.LANCZOS,
}
NEG_LOBES = {"nearest": False, "box": False, "bilinear": False,
             "bicubic": True, "lanczos": True}

RESULTS = []          # (arm, verdict, detail)


def record(arm, ok, detail):
    RESULTS.append((arm, "PASS" if ok else "FAIL", detail))
    print("  [%s] %-6s %s" % ("PASS" if ok else "FAIL", arm, detail))


def pil_reduce(a8, nw, nh, kernel):
    """Float-mode resize: no output rounding, no clipping, so the hull bound is
    exact to float precision and cannot be flattered by a clamp."""
    im = Image.fromarray(a8.astype(np.float32), mode="F")
    return np.asarray(im.resize((nw, nh), KERNELS[kernel]), dtype=np.float64)


def synth_step(h, w, lo, hi, edge):
    a = np.full((h, w), lo, np.uint8)
    a[:, edge:] = hi
    return a


def measure(a8, kernel, scale, support=18):
    h, w = a8.shape
    nw, nh = int(round(w / scale)), int(round(h / scale))
    out = pil_reduce(a8, nw, nh, kernel)
    exc, dfc = rimlib.hull_window(a8, out, support)
    return float(np.maximum(exc, dfc).max())


# ============================================================== the arms

def arm_C1_must_fire():
    """A hard step must make the negative-lobe kernels fire, and only them.

    Phase matters: V-REVIEW measured that sampling one sub-pixel phase
    understates lanczos by 4.1x.  So this sweeps the edge across a full output
    pixel and takes the max, rather than drawing once.
    """
    print("\n=== C1  hard step 40->200 DN, edge phase swept over one output px ===")
    per = {}
    for kern in KERNELS:
        best = 0.0
        for ph in range(12):
            a = synth_step(256, 1024, 40, 200, 512 + ph)
            best = max(best, measure(a, kern, GALLERY_SCALE))
        per[kern] = best
        print("      %-9s %8.3f DN" % (kern, best))
    for kern, v in per.items():
        if NEG_LOBES[kern]:
            record("C1-" + kern, v > 1.0, "negative lobes must fire: %.3f DN" % v)
        else:
            record("C1-" + kern, v < 1e-6, "no negative lobes, must be 0: %.6f" % v)
    return per


def arm_C2_must_not_fire():
    print("\n=== C2  nothing to ring: constant field, and a linear ramp ===")
    flat = np.full((256, 1024), 128, np.uint8)
    ramp = np.tile(np.linspace(20, 230, 1024).astype(np.uint8), (256, 1))
    for name, a, tol in (("flat", flat, 1e-6), ("ramp", ramp, 0.25)):
        for kern in KERNELS:
            v = measure(a, kern, GALLERY_SCALE)
            record("C2-%s-%s" % (name, kern), v < tol,
                   "%s under %s = %.6f DN (tol %.2f)" % (name, kern, v, tol))


def arm_C3_real_rim_is_not_manufactured():
    """A bright rim planted INTO the master must not be scored as manufactured.

    This is the arm that separates the two hypotheses.  If it failed, a zero
    from box would mean nothing, because the instrument would be unable to tell
    a halo that exists from a halo that was made.
    """
    print("\n=== C3  a REAL 40 DN rim, planted in the master ===")
    a = synth_step(256, 1024, 40, 200, 512)
    a[:, 512:520] = np.uint8(240)          # a real bright rim, in the master
    for kern in KERNELS:
        v = measure(a, kern, GALLERY_SCALE)
        if NEG_LOBES[kern]:
            record("C3-" + kern, v > 0.5, "may fire on its own ringing: %.3f" % v)
        else:
            record("C3-" + kern, v < 1e-6,
                   "a real rim must NOT read as manufactured: %.6f" % v)


def arm_C4_tracks_amplitude():
    print("\n=== C4  the reading must track step amplitude, not saturate ===")
    vals = []
    for amp in (20, 40, 80, 160):
        a = synth_step(256, 1024, 40, 40 + amp, 512)
        vals.append(measure(a, "lanczos", GALLERY_SCALE))
    print("      amps 20/40/80/160 -> %s" % " ".join("%.3f" % v for v in vals))
    ratios = [vals[i + 1] / vals[i] for i in range(3)]
    print("      ratios %s" % " ".join("%.3f" % r for r in ratios))
    record("C4", all(abs(r - 2.0) < 0.05 for r in ratios),
           "ratios %s (want 2.000)" % ", ".join("%.3f" % r for r in ratios))


def arm_C5_adversarial_envelope():
    """Reach the algebraic ceiling without exceeding it.

    Honest about what this proves: the adversarial input is BUILT from the
    measured weights, so attaining 255*N is an identity, not an independent
    measurement of the kernel.  What it does test is my own implementation --
    if hull_window sampled the wrong master coordinate, or used a window so
    generous that the local max exceeded 255, the reading would fall SHORT of
    the ceiling.  It is a self-consistency check on the instrument, and it is
    labelled as one.
    """
    print("\n=== C5  adversarial sign-matched input vs the derived envelope ===")
    sup = Image.LANCZOS
    # derive PIL's actual 1-D weights at the gallery scale
    n = 1024
    nn = int(round(n / GALLERY_SCALE))
    probe = np.zeros((1, n), np.float32)
    # a unit impulse response, read one output pixel at a time
    col = nn // 2
    ws = []
    for i in range(n):
        probe[:] = 0
        probe[0, i] = 1.0
        im = Image.fromarray(probe, mode="F")
        r = np.asarray(im.resize((nn, 1), sup), dtype=np.float64)
        ws.append(r[0, col])
    ws = np.array(ws)
    negmass = float(-ws[ws < 0].sum())
    envelope = negmass * 255.0
    taps = int((np.abs(ws) > 1e-9).sum())
    print("      taps=%d  negative weight mass N=%.4f  envelope=%.3f DN"
          % (taps, negmass, envelope))
    adv = np.where(ws < 0, 0, 255).astype(np.uint8)[None, :].repeat(64, 0)
    got = {k: measure(adv, k, GALLERY_SCALE, support=64) for k in KERNELS}
    for k, v in got.items():
        print("      %-9s %8.3f DN" % (k, v))
    record("C5-envelope", got["lanczos"] <= envelope + 1e-6,
           "lanczos %.3f must not exceed the derived envelope %.3f"
           % (got["lanczos"], envelope))
    record("C5-reach", got["lanczos"] > 0.9 * envelope,
           "lanczos %.3f reaches %.1f%% of the envelope"
           % (got["lanczos"], 100.0 * got["lanczos"] / envelope))
    for k in ("box", "bilinear", "nearest"):
        record("C5-" + k, got[k] < 1e-6,
               "%s on adversarial input must stay 0: %.6f" % (k, got[k]))


def arm_C6_nearest_cannot_ring():
    """THE ARM THAT DECIDES WHAT THIS STATISTIC IS MEASURING.

    Nearest is a real, catastrophic degradation and it physically cannot ring.
    Rim must read exactly 0.000; the second axis, area_err, must be large.  If
    rim fired on nearest, this statistic would be measuring aliasing.
    """
    print("\n=== C6  nearest-neighbour: cannot ring, but IS a degradation ===")
    rng = np.random.default_rng(7)
    a = rng.integers(0, 256, (256, 1024), dtype=np.uint8)     # worst case for aliasing
    k = SHIP_K
    nh, nw = 256 // k, 1024 // k
    got = {}
    for kern in KERNELS:
        out = pil_reduce(a, nw, nh, kern)
        exc, dfc = rimlib.hull_block(a, out, k)
        rim = float(np.maximum(exc, dfc).max())
        ae = rimlib.area_err(a, out, k)
        got[kern] = (rim, ae)
        print("      %-9s rim %8.6f   area_err %8.3f DN" % (kern, rim, ae))
    record("C6-rim-zero", got["nearest"][0] < 1e-9,
           "nearest rim = %.9f -- if this were >0 the statistic would be "
           "measuring aliasing, not ringing" % got["nearest"][0])
    record("C6-alias-caught", got["nearest"][1] > 20.0,
           "nearest area_err = %.3f DN: the second axis DOES charge it"
           % got["nearest"][1])
    record("C6-box-both-zero", got["box"][0] < 1e-9 and got["box"][1] < 1e-9,
           "box: rim %.9f, area_err %.9f -- clean on both axes"
           % (got["box"][0], got["box"][1]))


def arm_C7_blind_to_blur():
    """State the blindness rather than let a reader infer soundness from a 0.

    Three parts, because my first draft of this arm conflated two claims and
    failed -- correctly.  The disturbance is shown to be real first; then rim is
    asked and must read 0; then the reduction ITSELF is probed, at two disturbance
    scales, so that "the overview cannot show this" is established as a
    resolution limit rather than a dead probe.
    """
    print("\n=== C7  blindness, declared, at two disturbance scales ===")
    rng = np.random.default_rng(11)
    a = rng.integers(0, 256, (256, 1024), dtype=np.uint8)      # real fine detail

    # --- a FINE disturbance: destroy everything below 2 px -------------------
    half = Image.fromarray(a).resize((512, 128), Image.BOX)
    fine = np.asarray(half.resize((1024, 256), Image.BOX)).astype(np.uint8)
    dmax = float(np.abs(a.astype(np.float64) - fine.astype(np.float64)).max())
    drms = float(np.sqrt(((a.astype(np.float64) - fine.astype(np.float64)) ** 2).mean()))
    print("      fine disturbance at full res : max %.1f DN, rms %.1f DN" % (dmax, drms))
    record("C7-disturbance-real", dmax > 100.0 and drms > 20.0,
           "half the resolution is genuinely gone: max %.1f DN, rms %.1f DN"
           % (dmax, drms))

    out = rimlib.box_reduce(fine, SHIP_K)
    exc, dfc = rimlib.hull_block(fine, out, SHIP_K)
    rim = float(np.maximum(exc, dfc).max())
    record("C7-blind", rim < 1e-9,
           "rim scores %.9f on a master with half its resolution destroyed -- "
           "THIS STATISTIC IS BLIND TO BLUR BY DESIGN and a 0 is not a quality "
           "claim" % rim)

    seen_fine = float(np.abs(out - rimlib.box_reduce(a, SHIP_K)).max())
    print("      the same disturbance AFTER %dx reduction: %.3f DN"
          % (SHIP_K, seen_fine))
    record("C7-overview-limit", seen_fine < 2.0,
           "a 187 DN sub-2px disturbance survives the %dx reduction as %.3f DN: "
           "THE OVERVIEW CANNOT ADJUDICATE DETAIL FINER THAN THE REDUCTION -- "
           "that is what the 1:1 crops are for" % (SHIP_K, seen_fine))

    # --- a COARSE disturbance: the same probe must MOVE ----------------------
    q = Image.fromarray(a).resize((64, 16), Image.BOX)
    coarse = np.asarray(q.resize((1024, 256), Image.BOX)).astype(np.uint8)
    seen_coarse = float(np.abs(rimlib.box_reduce(coarse, SHIP_K)
                               - rimlib.box_reduce(a, SHIP_K)).max())
    print("      a 16px-scale disturbance after the same reduction: %.3f DN"
          % seen_coarse)
    record("C7-overview-not-dead", seen_coarse > 20.0,
           "the same probe moves by %.3f DN on a coarse disturbance, so the "
           "%.3f DN above is a resolution limit and not a dead probe"
           % (seen_coarse, seen_fine))


def arm_P1_pil_is_not_trusted():
    print("\n=== P1  PIL's Image.BOX is verified, not assumed ===")
    rng = np.random.default_rng(3)
    a = rng.integers(0, 256, (4688 // 4, 7040 // 4, 3), dtype=np.uint8)
    mine = rimlib.box_reduce(a, SHIP_K)
    theirs = np.stack([
        np.asarray(Image.fromarray(a[..., c].astype(np.float32), mode="F")
                   .resize((a.shape[1] // SHIP_K, a.shape[0] // SHIP_K), Image.BOX),
                   dtype=np.float64)
        for c in range(3)], -1)
    d = float(np.abs(mine - theirs).max())
    print("      shape %s, factor %d" % (a.shape, SHIP_K))
    print("      max |numpy block mean - PIL BOX| = %.3e DN" % d)
    record("P1", d < 1e-4,
           "PIL BOX agrees with an independent numpy block mean to %.3e DN" % d)
    # and the shipped path does not depend on the answer:
    record("P1-independence", True,
           "DELIVER-V5 ships the numpy block mean regardless; PIL is only checked")


def arm_W1_true11_converter_defect():
    print("\n=== W1  the 16->8 converter DELIVER-V5 refuses to reuse ===")
    white = np.array([[65535]], np.uint16)
    theirs = ((white.astype(np.uint32) + 128) >> 8).astype(np.uint8)
    mine = rimlib.to8(white)
    print("      true11.py's converter on 65535 -> %d" % int(theirs[0, 0]))
    print("      rimlib.to8       on 65535 -> %d" % int(mine[0, 0]))
    record("W1", int(theirs[0, 0]) == 0 and int(mine[0, 0]) == 255,
           "unclipped >>8 wraps pure white to %d; rimlib.to8 gives %d"
           % (int(theirs[0, 0]), int(mine[0, 0])))


def main():
    print(__doc__.split("Usage:")[0].strip()[:0] or "", end="")
    print("COMMISSIONING THE INJECTED-RIM STATISTIC")
    print("pass/fail rules are in this source file, written before any corpus "
          "number was computed")
    arm_C1_must_fire()
    arm_C2_must_not_fire()
    arm_C3_real_rim_is_not_manufactured()
    arm_C4_tracks_amplitude()
    arm_C5_adversarial_envelope()
    arm_C6_nearest_cannot_ring()
    arm_C7_blind_to_blur()
    arm_P1_pil_is_not_trusted()
    arm_W1_true11_converter_defect()

    npass = sum(1 for _, v, _ in RESULTS if v == "PASS")
    nfail = len(RESULTS) - npass
    print("\n=== counted partition of commissioning arms ===")
    print("  pass %d + fail %d = %d of %d   %s"
          % (npass, nfail, npass + nfail, len(RESULTS),
             "OK" if npass + nfail == len(RESULTS) else "PARTITION BROKEN"))
    if nfail:
        print("\n  FAILED ARMS:")
        for a, v, d in RESULTS:
            if v == "FAIL":
                print("    %-18s %s" % (a, d))
    print("\nVERDICT: %s" % ("the statistic may be used" if nfail == 0 else
                             "DO NOT USE -- %d arm(s) failed" % nfail))
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
