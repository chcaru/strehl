r"""Why did 99,880 corrected samples change nothing, and 49,551 change everything?

THE OBSERVATION THAT FORCED THIS PROBE. Rendering the same two subjects with
STREHL_DEFECT off and on, from one binary, changing nothing else:

  109MSDCF        samples changed 99,880 over 22 frames -> output BIT-IDENTICAL
  coffee-bubbles  samples changed 49,551 over 19 frames -> 98.515% of output samples moved

Half as many corrected samples produced a hundred million times more output
change. The count of samples the corrector touched does not predict the output
at all, and until that is explained no ON-vs-OFF number from these renders means
anything.

TWO CANDIDATE EXPLANATIONS, AND THIS SCRIPT TESTS BOTH RATHER THAN PICKING ONE.

  CLIP     109MSDCF is rendered at +2.60 stops, coffee-bubbles at -0.26. If the
           mote neighbourhoods are already at or near the top of the range, a
           correction that brightens them lands in saturated output and both arms
           write the same number. That would make the correction real but
           invisible on that subject, which is a finding about where correction
           matters -- not a wiring defect.

  TONE     stack.rs folds the exposure gain into a normalisation derived from
           image statistics. Brightening a few thousand samples per frame can
           move that statistic, rescaling EVERY pixel by a small factor. That
           would explain a 98.5% change whose mean magnitude is under 4 DN out of
           65,535, and it is a CONFOUND: a global tone shift would move every
           whole-image statistic in the print gate for reasons that have nothing
           to do with dust.

HOW EACH IS DECIDED, WITH A NULL FOR EACH.

  CLIP is measured as the fraction of samples at the top of the range inside the
  mote neighbourhoods, in BOTH arms, against the same fraction over the whole
  frame as the null. A high clip fraction that is equally high outside the motes
  explains nothing.

  TONE is decided by fitting one global affine map on -> a*off + b over a sample
  of pixels drawn AWAY from every mote, then asking how much of the whole-frame
  change that single pair of numbers accounts for. The null is the identity
  (a=1, b=0): if the fit does not move away from identity, there is no global
  shift and the explanation is rejected. Sites near the motes are excluded from
  the FIT and then used as the held-out test, so the fit cannot absorb the very
  signal it is supposed to isolate.

The mote coordinates are PARSED OUT OF THE RENDER LOG, not written here, so this
probe cannot test a site the run did not actually correct.
"""
import io
import json
import os
import re
import sys

import numpy as np
import tifffile

ROOT = r"C:\dev\strehl-out\BUILD-DEFECT\arms"
REPO = r"C:\dev\blog\death-of-software\projects\strehl"
OUTDIR = os.path.join(REPO, "experiments", "BUILD-DEFECT", "out")

# A quad is 2x2 photosites, so a quad coordinate doubles into the CFA plane and
# the rendered master is one output pixel per photosite. Parsed sites are quad
# coordinates; RAD_OUT is the half-width of the neighbourhood examined around
# each, in output pixels, chosen to cover the mote radius measured in section 13
# (38 quads = 76 output px) with margin.
RAD_OUT = 120
TOP_FRAC = 0.999  # "at the top of the range" as a fraction of full scale
N_FIT = 400000


def parse_sites(log):
    """Mote coordinates and what the run decided to do with each.

    Parsed from the run's own banner. A probe that tests coordinates typed into
    itself can report a clean result about a site the render never touched.
    """
    txt = io.open(log, encoding="utf-8", errors="replace").read()
    out = []
    for m in re.finditer(r"site \(\s*(\d+),\s*(\d+)\): depth ([-\d.]+)% \(map ([-\d.]+)%\), "
                         r"p ([\d.]+), present ([\d.]+) -> (.+)", txt):
        act = m.group(7).strip()
        out.append({"qx": int(m.group(1)), "qy": int(m.group(2)),
                    "depth_pct": float(m.group(3)), "map_pct": float(m.group(4)),
                    "p": float(m.group(5)), "present": float(m.group(6)),
                    "action": act, "corrected": act.startswith("CORRECT")})
    changed = re.search(r"samples changed\s*:\s*(\d+)\s+over\s+(\d+)", txt)
    quads = re.search(r"defect map\s*:\s*(\d+) hot, (\d+) dust quads", txt)
    return out, {"samples_changed": int(changed.group(1)) if changed else None,
                 "frames": int(changed.group(2)) if changed else None,
                 "dust_quads": int(quads.group(2)) if quads else None}


def mote_mask(shape, sites, rad):
    h, w = shape[:2]
    m = np.zeros((h, w), bool)
    for s in sites:
        if not s["corrected"]:
            continue
        cy, cx = s["qy"] * 2, s["qx"] * 2
        m[max(0, cy - rad):min(h, cy + rad), max(0, cx - rad):min(w, cx + rad)] = True
    return m


def run(sub):
    off = tifffile.imread(os.path.join(ROOT, sub + "--off.tiff"))
    on = tifffile.imread(os.path.join(ROOT, sub + "--on.tiff"))
    sites, meta = parse_sites(os.path.join(ROOT, sub + "--on.log"))
    corr = [s for s in sites if s["corrected"]]
    rec = {"subject": sub, "sites": sites, "n_corrected_sites": len(corr), **meta}

    d = on.astype(np.int32) - off.astype(np.int32)
    nz = d != 0
    rec["frac_samples_moved"] = float(nz.mean())
    rec["abs_max"] = int(np.abs(d).max())

    near = mote_mask(off.shape, sites, RAD_OUT)
    far = ~near
    rec["frac_area_near_motes"] = float(near.mean())

    # ---- CLIP ----
    full = float(np.iinfo(off.dtype).max)
    top = TOP_FRAC * full
    rec["clip"] = {
        "near_off": float((off[near] >= top).mean()) if near.any() else None,
        "near_on": float((on[near] >= top).mean()) if near.any() else None,
        "far_off": float((off[far] >= top).mean()),
        "far_on": float((on[far] >= top).mean()),
    }

    # ---- TONE ----
    # Fit on pixels AWAY from every mote so the global term cannot absorb the
    # local correction, then test on the pixels near the motes.
    rng = np.random.default_rng(7)
    fy, fx = np.nonzero(far)
    take = rng.choice(fy.size, size=min(N_FIT, fy.size), replace=False)
    xo = off[fy[take], fx[take]].astype(np.float64).ravel()
    yo = on[fy[take], fx[take]].astype(np.float64).ravel()
    a, b = np.polyfit(xo, yo, 1)
    rec["tone"] = {"a": float(a), "b": float(b), "n_fit": int(xo.size)}

    pred = np.clip(a * off.astype(np.float64) + b, 0, full)
    resid_after = np.abs(pred - on.astype(np.float64))
    resid_before = np.abs(off.astype(np.float64) - on.astype(np.float64))
    rec["tone"]["mean_abs_before"] = float(resid_before.mean())
    rec["tone"]["mean_abs_after"] = float(resid_after.mean())
    rec["tone"]["explained_frac"] = (
        float(1.0 - resid_after.mean() / resid_before.mean()) if resid_before.mean() > 0 else None)
    rec["tone"]["near_mean_abs_before"] = float(resid_before[near].mean()) if near.any() else None
    rec["tone"]["near_mean_abs_after"] = float(resid_after[near].mean()) if near.any() else None
    rec["tone"]["far_mean_abs_before"] = float(resid_before[far].mean())
    rec["tone"]["far_mean_abs_after"] = float(resid_after[far].mean())
    del off, on, d, nz, pred, resid_after, resid_before
    return rec


def verdict(r):
    """Name the mechanism, and refuse to name one when the evidence does not."""
    if r["frac_samples_moved"] == 0.0:
        clipped = (r["clip"]["near_off"] or 0.0) > 0.5
        if clipped:
            return ("CLIPPED", "the corrector changed %d samples but the mote "
                    "neighbourhoods are %.1f%% saturated in BOTH arms, so the "
                    "correction lands above the top of the range"
                    % (r["samples_changed"], 100 * r["clip"]["near_off"]))
        return ("UNEXPLAINED", "the corrector changed %d samples and no output "
                "sample moved, and saturation does not account for it (%.1f%% "
                "of near-mote samples at the top of the range)"
                % (r["samples_changed"], 100 * (r["clip"]["near_off"] or 0.0)))
    t = r["tone"]
    off_identity = abs(t["a"] - 1.0) > 1e-6 or abs(t["b"]) > 1e-3
    if off_identity and (t["explained_frac"] or 0) > 0.5:
        return ("GLOBAL TONE SHIFT", "a single global affine map a=%.8f b=%+.4f "
                "explains %.1f%% of the whole-frame change; away from the motes "
                "it removes %.3f DN of %.3f DN"
                % (t["a"], t["b"], 100 * t["explained_frac"],
                   t["far_mean_abs_before"] - t["far_mean_abs_after"],
                   t["far_mean_abs_before"]))
    if not off_identity:
        return ("LOCAL ONLY", "the global fit did not move off identity "
                "(a=%.8f, b=%+.4f), so the change is not a tone shift" % (t["a"], t["b"]))
    return ("MIXED", "a global fit a=%.8f b=%+.4f explains only %.1f%% of the change"
            % (t["a"], t["b"], 100 * (t["explained_frac"] or 0)))


def main():
    subs = sys.argv[1:] or ["coffee-bubbles", "109MSDCF"]
    recs = []
    for s in subs:
        print("=" * 78)
        print(s, flush=True)
        r = run(s)
        recs.append(r)
        print("  dust quads mapped      %s" % r["dust_quads"])
        print("  sites confirmed        %d of %d" % (r["n_corrected_sites"], len(r["sites"])))
        for st in r["sites"]:
            print("    (%5d,%5d) depth %7.3f%% map %7.3f%% p %.4f  %s"
                  % (st["qx"], st["qy"], st["depth_pct"], st["map_pct"], st["p"], st["action"]))
        print("  samples changed        %s over %s frames" % (r["samples_changed"], r["frames"]))
        print("  output samples moved   %.6f%%  (|delta| max %d)"
              % (100 * r["frac_samples_moved"], r["abs_max"]))
        print("  area near motes        %.4f%% of the frame" % (100 * r["frac_area_near_motes"]))
        c = r["clip"]
        print("  at top of range        near-mote off %.2f%% on %.2f%%   |   elsewhere off %.2f%% on %.2f%%"
              % (100 * (c["near_off"] or 0), 100 * (c["near_on"] or 0),
                 100 * c["far_off"], 100 * c["far_on"]))
        t = r["tone"]
        print("  global affine fit      a=%.8f  b=%+.4f  (fitted on %d pixels away from motes)"
              % (t["a"], t["b"], t["n_fit"]))
        print("  mean |on-off|          %.4f DN, after removing the global fit %.4f DN"
              % (t["mean_abs_before"], t["mean_abs_after"]))
        print("    away from motes      %.4f -> %.4f DN" % (t["far_mean_abs_before"], t["far_mean_abs_after"]))
        print("    near the motes       %s -> %s DN"
              % ("n/a" if t["near_mean_abs_before"] is None else "%.4f" % t["near_mean_abs_before"],
                 "n/a" if t["near_mean_abs_after"] is None else "%.4f" % t["near_mean_abs_after"]))
        v, why = verdict(r)
        r["verdict"] = v
        r["why"] = why
        print("  VERDICT                %s" % v)
        print("                         %s" % why)
        print(flush=True)

    print("=" * 78)
    print("PARTITION -- every subject examined lands in exactly one mechanism")
    kinds = ("CLIPPED", "GLOBAL TONE SHIFT", "LOCAL ONLY", "MIXED", "UNEXPLAINED")
    for k in kinds:
        print("  %-20s %2d" % (k, sum(1 for r in recs if r["verdict"] == k)))
    tot = sum(sum(1 for r in recs if r["verdict"] == k) for k in kinds)
    print("  %-20s %2d  (must equal %d)" % ("TOTAL", tot, len(recs)))
    if tot != len(recs):
        raise SystemExit("PARTITION DOES NOT SUM")

    p = os.path.join(OUTDIR, "71-arm-mechanism.json")
    json.dump(recs, io.open(p, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % os.path.relpath(p, REPO))


if __name__ == "__main__":
    main()
