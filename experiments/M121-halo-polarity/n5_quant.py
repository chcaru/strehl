"""N5 -- does the PIL uint8 narrowing move MY statistic?

ORCH's fleet notice (2026-08-24) gives two triage questions:

    (a) is my statistic absolute?
    (b) does it divide a small quantity by a large one?

My answers are NO and **YES**.  The rim is

    rim = (p(+d) - hi) / A ,   A = hi - lo

-- a small overshoot over a large edge amplitude, both drawn from the same
pixels of the same read.  (a) is safe by construction.  (b) is exactly the
case ORCH flags as compressing toward a clean null, "the hardest error here to
catch, because nobody re-examines an arm that showed no effect".

**M121 reports a clean null.**  Row two of the headline table
(bright object / dark surround) is +0.0009 with 50% positive.  That is the
arm nobody would re-examine.  So I re-examine it.

M121 never read a pixel through PIL -- `m121_io.load_u16` is tifffile plus an
immediate uint16 assert, and the only PIL calls in this milestone are
`Image.fromarray(...).save(...)`.  But "my reader was correct" is an assertion
about code.  This script is a MEASUREMENT of consequence: it plants the actual
defect and reports what it would have done to the headline and to the null.

Structure, in the order the project requires:

  1. Reproduce fact 1615 live, on this machine, on this data.
  2. COMMISSION an arithmetic narrowing model byte-against-PIL, and hard-error
     if it does not match -- a model of the defect that was never checked
     against the defect is worth nothing.
  3. Plant it and re-run the exact E2 headline at the exact same edges.
  4. Report clean vs narrowed for the headline AND for the null.

Outputs: C:\\dev\\strehl-out\\M121\\n5\\n5-quant.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from m121_io import OUT, arm_path, load_u16, luma, sha256  # noqa: E402
from runner import scan  # noqa: E402
import e2_polarity as E2  # noqa: E402

N5 = OUT / "n5"

# A crop with real structure in it, used only to commission the model.
# Chosen as the busiest 512 tile of the shipped arm by mean |grad| (see the
# probe in the report's script index); the arm is 2344x3516 after 2x binning.
CROP = (0, 512, 512, 1024)   # y0, y1, x0, x1


def distinct_levels(a: np.ndarray) -> int:
    return int(np.unique(a).size)


def measure_pil_narrowing(rgb: np.ndarray) -> dict:
    """Reproduce fact 1615 on this machine, and return PIL's actual output.

    Writes a genuine 16-bit RGB TIFF and reads it back the hazardous way,
    `np.asarray(Image.open(p))`.  This is the one place in M121 that PIL is
    pointed at pixels, and it is pointed at them deliberately, to characterise
    the defect rather than to measure the subject.
    """
    from PIL import Image

    N5.mkdir(parents=True, exist_ok=True)
    p = N5 / "commission-crop.tif"
    y0, y1, x0, x1 = CROP
    crop = np.ascontiguousarray(rgb[y0:y1, x0:x1, :])
    assert crop.dtype == np.uint16, f"crop is {crop.dtype}"
    tifffile.imwrite(str(p), crop)

    back_tf = tifffile.imread(str(p))
    assert back_tf.dtype == np.uint16, "tifffile round-trip lost the depth"
    assert np.array_equal(back_tf, crop), "tifffile round-trip was not exact"

    pil = np.asarray(Image.open(str(p)))

    return {
        "crop": list(CROP),
        "written_dtype": "uint16",
        "tifffile_readback_dtype": str(back_tf.dtype),
        "tifffile_exact": True,
        "pil_readback_dtype": str(pil.dtype),
        "levels_true": distinct_levels(crop),
        "levels_pil": distinct_levels(pil),
        "_crop": crop,
        "_pil": pil,
    }


def commission_model(crop: np.ndarray, pil: np.ndarray) -> str:
    """Find an arithmetic narrowing that reproduces PIL EXACTLY, or hard-error.

    Applying a *guessed* narrowing to the full frame would be modelling the
    defect rather than planting it.  The model is only allowed downstream if it
    is byte-identical to what PIL actually did.
    """
    candidates = {
        "shift8": (crop >> 8).astype(np.uint8),
        "div257_floor": (crop // 257).astype(np.uint8),
        "div257_round": np.rint(crop / 257.0).clip(0, 255).astype(np.uint8),
    }
    if pil.ndim == 3 and pil.shape[2] > 3:
        pil = pil[:, :, :3]
    for name, cand in candidates.items():
        if cand.shape == pil.shape and np.array_equal(cand, pil):
            print(f"  narrowing model COMMISSIONED: '{name}' is byte-identical "
                  f"to PIL over {cand.size} samples")
            return name
    diffs = {n: int(np.abs(c.astype(int) - pil.astype(int)).max())
             for n, c in candidates.items() if c.shape == pil.shape}
    raise SystemExit(
        "N5 HARD ERROR: no candidate narrowing reproduces PIL byte-for-byte "
        f"(max |diff| per candidate: {diffs}).  Refusing to plant a modelled "
        "defect that was never validated against the real one."
    )


def apply_narrowing(rgb: np.ndarray, model: str) -> np.ndarray:
    """Narrow to uint8 the way PIL does, then re-expand to the 16-bit DN scale.

    The re-expansion (x257) is what makes the two runs comparable: it restores
    the scale so `MIN_AMPLITUDE = 2000 DN` still means the same thing and the
    dimensionless rim is read against a like-for-like amplitude.  It restores
    the RANGE; it cannot restore the LEVELS, which is the damage.
    """
    if model == "shift8":
        narrowed = (rgb >> 8).astype(np.uint8)
    elif model == "div257_floor":
        narrowed = (rgb // 257).astype(np.uint8)
    elif model == "div257_round":
        narrowed = np.rint(rgb / 257.0).clip(0, 255).astype(np.uint8)
    else:
        raise SystemExit(f"unknown narrowing model {model!r}")
    return narrowed.astype(np.uint16) * 257


def row(tab, key):
    """Pull one polarity row out of e2_polarity.polarity_table()'s output.

    The table also carries non-row entries (`read_band` is a list,
    `out_of_band` a string), so anything that is not a dict of the expected
    shape is skipped rather than coerced.
    """
    if tab is None:
        return None
    r = tab.get(key)
    if not isinstance(r, dict):
        return None
    return {"n": r.get("n"), "rim": r.get("surround_rim"),
            "frac_pos": r.get("frac_positive"),
            "ci": [r.get("lo95"), r.get("hi95")],
            "w50": r.get("w50"), "cutoff": r.get("cutoff")}


def main():
    N5.mkdir(parents=True, exist_ok=True)
    out: dict = {}

    max_rise = E2.commissioned_max_rise()
    print(f"commissioned envelope: 10-90 rise <= {max_rise:.2f} px")

    p = arm_path("armM4-gate4-binlin")
    print(f"loading {p.name} ...")
    rgb = load_u16(p)
    assert rgb.dtype == np.uint16, f"shipped arm came back {rgb.dtype}"
    out["arm"] = {"path": str(p), "sha256": sha256(p), "dtype": str(rgb.dtype),
                  "shape": list(rgb.shape)}

    # ---- 1 + 2: reproduce fact 1615, then commission the model -----------
    print("\n[1] reproducing fact 1615 on this machine ...")
    m = measure_pil_narrowing(rgb)
    crop, pil = m.pop("_crop"), m.pop("_pil")
    print(f"  wrote a genuine uint16 RGB TIFF; tifffile reads it back "
          f"{m['tifffile_readback_dtype']} (exact)")
    print(f"  PIL reads the SAME FILE back as {m['pil_readback_dtype']}")
    print(f"  distinct levels: {m['levels_true']} -> {m['levels_pil']} "
          f"({m['levels_true'] / max(m['levels_pil'], 1):.1f}x loss)")
    if m["pil_readback_dtype"] != "uint8":
        print("  NOTE: PIL did NOT narrow here; fact 1615 may be "
              "version-dependent on this machine.")
    out["fact_1615_live"] = m

    print("\n[2] commissioning the narrowing model against PIL ...")
    model = commission_model(crop, pil)
    out["narrowing_model"] = model

    # ORCH's refinement: damage scales with the OCCUPIED range, not the full
    # 16-bit range.  Measure it on the crop I actually commissioned against.
    occ_lo, occ_hi = int(crop.min()), int(crop.max())
    out["occupied_range"] = {
        "lo": occ_lo, "hi": occ_hi, "span_dn": occ_hi - occ_lo,
        "levels_true": m["levels_true"], "levels_after": m["levels_pil"],
    }
    print(f"  occupied range {occ_lo}..{occ_hi} ({occ_hi - occ_lo} DN) -> "
          f"{m['levels_pil']} levels survive")

    # ---- 3: plant it and re-run the exact E2 headline --------------------
    print("\n[3] planting the defect and re-running the E2 headline ...")
    clean = luma(rgb)
    dirty = luma(apply_narrowing(rgb, model))
    del rgb

    frames = {n: luma(load_u16(arp)) for n, arp in
              ((n, arp) for n, arp in ((f, arm_path(f)) for f in E2.FRAMES))}
    fmax = np.max(np.stack([E2.focus_field(f) for f in frames.values()]), axis=0)
    classify = E2.make_classifier(fmax)
    del frames, fmax

    kw = dict(isolation_frac=E2.ISO, flat_tol=E2.FLAT_TOL, classify=classify,
              min_amplitude=E2.MIN_AMPLITUDE)

    r_detect = scan(clean, label="N5 detect (clean, tifffile uint16)",
                    grad_percentile=E2.GRAD_PCT, max_edges=E2.MAX_EDGES,
                    collect_edges=True, max_rise=max_rise, verbose=False, **kw)
    donor = r_detect["kept_edges"]
    print(f"  donor edges from the clean read: {donor.shape[0]}")

    # Both arms are then scored AT THE SAME EDGES with the same acceptance
    # code, so the only difference between them is the bit depth.  Scoring the
    # clean arm on its own full detection instead would compare two different
    # edge sets and confound the plant with a change of sample.
    r_clean = scan(clean, label="N5 clean (tifffile, uint16)",
                   edges=donor, max_rise=None, **kw)
    r_dirty = scan(dirty, label="N5 narrowed (PIL uint8 -> x257)",
                   edges=donor, max_rise=None, **kw)

    # (b) THE TRUE COUNTERFACTUAL.  The matched-edge run above isolates the
    # effect on the pixel values, but an agent who read through PIL would also
    # have DETECTED on the narrowed image.  So re-run the headline end to end
    # on the narrowed arm, with the headline's own settings, and compare the
    # numbers that would actually have been reported.  The matched-edge donor
    # is the pair subset, which starves the headline class; this run does not.
    print("\n[3b] true counterfactual: full headline re-run on the narrowed arm ...")
    r_cf = scan(dirty, label="N5 counterfactual (narrowed, own detection)",
                grad_percentile=E2.GRAD_PCT, max_edges=E2.MAX_EDGES,
                max_rise=max_rise, verbose=False, **kw)
    r_hl = scan(clean, label="N5 headline (clean, own detection)",
                grad_percentile=E2.GRAD_PCT, max_edges=E2.MAX_EDGES,
                max_rise=max_rise, verbose=False, **kw)
    t_hl, t_cf = E2.polarity_table(r_hl), E2.polarity_table(r_cf)
    out["headline_clean"] = {k: row(t_hl, k) for k in t_hl}
    out["headline_narrowed"] = {k: row(t_cf, k) for k in t_cf}

    t_clean = E2.polarity_table(r_clean)
    t_dirty = E2.polarity_table(r_dirty)

    out["clean"] = {k: row(t_clean, k) for k in t_clean}
    out["narrowed"] = {k: row(t_dirty, k) for k in t_dirty}
    out["donor_edges"] = int(donor.shape[0])

    # ---- 4: the verdict --------------------------------------------------
    print("\n" + "=" * 74)
    print("N5 -- effect of the PIL uint8 narrowing on M121's statistic")
    print("=" * 74)
    hdr = f"{'row':<34}{'clean':>12}{'narrowed':>12}{'shift':>12}"
    print(hdr)
    print("-" * 74)
    verdict = {}
    for key in t_clean:
        a, b = row(t_clean, key), row(t_dirty, key)
        if a is None or b is None or a["rim"] is None or b["rim"] is None:
            continue
        d = b["rim"] - a["rim"]
        verdict[key] = {"clean": a["rim"], "narrowed": b["rim"], "shift": d,
                        "n_clean": a["n"], "n_narrowed": b["n"]}
        print(f"{key:<34}{a['rim']:>+12.4f}{b['rim']:>+12.4f}{d:>+12.4f}")
    out["verdict"] = verdict
    print("-" * 74)

    print("\n" + "=" * 74)
    print("N5b -- TRUE COUNTERFACTUAL: what the headline would have READ")
    print("=" * 74)
    print(f"{'row':<34}{'clean':>12}{'narrowed':>12}{'shift':>12}{'n':>8}")
    print("-" * 74)
    cf = {}
    for key in t_hl:
        a, b = row(t_hl, key), row(t_cf, key)
        if a is None or b is None or a["rim"] is None or b["rim"] is None:
            continue
        d = b["rim"] - a["rim"]
        cf[key] = {"clean": a["rim"], "narrowed": b["rim"], "shift": d,
                   "n_clean": a["n"], "n_narrowed": b["n"],
                   "frac_pos_clean": a["frac_pos"],
                   "frac_pos_narrowed": b["frac_pos"]}
        print(f"{key:<34}{a['rim']:>+12.4f}{b['rim']:>+12.4f}{d:>+12.4f}"
              f"{a['n']:>5}/{b['n']:<3}")
    out["counterfactual"] = cf
    print("-" * 74)

    # One row moved far more than the others.  ORCH's refinement says damage
    # scales with the OCCUPIED range, so the suspicion is that that class sits
    # on lower-amplitude edges.  Measure it rather than assert it.
    print("\nedge amplitude by class (clean arm), against the -0.0744 outlier:")
    amp = {}
    for name, side, want in (("dark_object_bright_surround", "bright", -1),
                             ("bright_object_dark_surround", "dark", +1),
                             ("undecided_bright_side", "bright", 0),
                             ("undecided_dark_side", "dark", 0)):
        s = r_hl.get(side)
        if s is None or "amps" not in s:
            continue
        sel = np.asarray(s["obj"]) == want
        A = np.asarray(s["amps"])[sel]
        if A.size == 0:
            continue
        amp[name] = {"n": int(A.size), "median_dn": float(np.median(A)),
                     "p10_dn": float(np.percentile(A, 10)),
                     "levels_after_narrowing": float(np.median(A) / 257.0)}
        print(f"  {name:<34} n={A.size:<4} median A={np.median(A):8.0f} DN  "
              f"p10={np.percentile(A, 10):8.0f} DN  "
              f"-> {np.median(A) / 257.0:5.1f} levels survive")
    out["amplitude_by_class"] = amp

    with open(N5 / "n5-quant.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {N5 / 'n5-quant.json'}")


if __name__ == "__main__":
    main()
