"""
05-judged-artefacts.py -- measure the images the owner actually judged.

WHY. The orchestrator's correction to this milestone's brief retracts the claim
that exposure is "the most likely single largest contributor" to the owner's
verdict, and folds fact 1344: the renders he judged were NOT the gallery, they
were `C:\\dev\\strehl-out\\*.png` written 2026-08-23 23:37-23:39, and they
carried FIVE defects at once. I am asked to add a paragraph naming them.

I do not republish another agent's measurement as mine (rule 43, and my own
SS4.6 in this report). Fact 1344's load-bearing numbers are the pixel dimensions
and the described defects. Both are cheap to check directly, so I check them.

PRE-REGISTERED READINGS, fixed before running:

  BINNING.   fact 1344 claims 3516x2344 = 8.24 MP, "exactly half of 7032x4688
             in each direction". CONFIRMED if the TIFs read 3516x2344 and the
             full-resolution capture is 7032x4688. REFUTED if either differs.
             The full-res figure comes from the ARW, not from fact 1344.

  FLAT TONE. If these renders are underexposed, p99.9 of luma sits far below
             1.0. CONFIRMED if p99.9 < 0.5 (i.e. more than 1 stop of headroom
             unused on the DISPLAY, not on the sensor). This is the same
             statistic `color.rs` AUTO_EXPOSURE_PERCENTILE uses, deliberately,
             so that the number is comparable to the shipped chooser's.

  GREY CAST. "No colour management" should leave the channels un-white-balanced.
             The camera's cam_wb is [2631, 1024, 1606], i.e. R and B need
             ~2.6x and ~1.6x relative to G. So an UNMANAGED render should read
             R and B DEPRESSED relative to G. CONFIRMED if mean(G) exceeds both
             mean(R) and mean(B) by a wide margin. REFUTED if the channels are
             already balanced.

  CONTROL (positive). `bee3-g0.tif` / `bee3-g1.tif` were written 10 minutes
             later, 23:47, by a different turn. They are NOT part of the judged
             set. If my instrument is working, they should still read as
             half-resolution -- the binning defect was not fixed in 10 minutes
             -- which tells me the measurement is reading the property and not
             the filename. A second control: `docs/captures-needed.md` SS22
             measures headroom on the RAW; my p99.9 here is on the RENDER. If
             these agreed exactly, I would suspect I had measured the same
             thing twice.

  PLACEBO.   The gallery renders under `C:\\dev\\strehl-out\\ORCH-gallery\\`,
             if present, went through the exposure post-process. They must NOT
             read as underexposed. If they do, my luma statistic is broken.

READ-ONLY. This script opens files and writes one JSON under its own OUT dir.
It never writes to C:\\dev\\strehl-out\\*.tif or to D:\\.
"""

import json
import os
import glob
import datetime

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M105"
JUDGED_DIR = r"C:\dev\strehl-out"

# Rec.709 luma on linear light. Not a constant of strehl's code (rule 34):
# these are the ITU-R BT.709 primaries' luminance coefficients.
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)

# The capture's full sensor dimensions, to be read from the RAW, not asserted.
FULL_W, FULL_H = 7032, 4688


def srgb_to_linear(a):
    a = a.astype(np.float64)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def measure(path):
    arr = tifffile.imread(path)
    if arr.ndim == 2:
        arr = arr[:, :, None]
    h, w = arr.shape[0], arr.shape[1]
    nch = arr.shape[2]

    maxval = float(np.iinfo(arr.dtype).max) if np.issubdtype(arr.dtype, np.integer) else 1.0
    norm = arr.astype(np.float64) / maxval

    # These renders are sRGB-encoded (they are the --srgb viewing path), so
    # linearise before taking any photometric statistic.
    lin = srgb_to_linear(norm)

    if nch >= 3:
        ch_means = [float(lin[:, :, i].mean()) for i in range(3)]
        luma = lin[:, :, :3] @ LUMA
    else:
        ch_means = [float(lin[:, :, 0].mean())] * 3
        luma = lin[:, :, 0]

    p999 = float(np.percentile(luma, 99.9, method="inverted_cdf"))
    stops_to_090 = float(np.log2(0.90 / p999)) if p999 > 0 else float("nan")

    st = os.stat(path)
    return {
        "file": os.path.basename(path),
        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "width": w,
        "height": h,
        "megapixels": round(w * h / 1e6, 2),
        "channels": nch,
        "dtype": str(arr.dtype),
        "is_half_of_full_capture": (w * 2 == FULL_W and h * 2 == FULL_H),
        "linear_channel_means": [round(c, 6) for c in ch_means],
        "green_over_red": round(ch_means[1] / ch_means[0], 4) if ch_means[0] > 0 else None,
        "green_over_blue": round(ch_means[1] / ch_means[2], 4) if ch_means[2] > 0 else None,
        "luma_p99_9_linear": round(p999, 6),
        "stops_below_target_0_90": round(stops_to_090, 3),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    result = {"judged": [], "control_2347": [], "placebo_gallery": []}

    for name in ("bee3-full.tif", "lavendar.tif", "marker.tif"):
        p = os.path.join(JUDGED_DIR, name)
        if os.path.exists(p):
            result["judged"].append(measure(p))

    for name in ("bee3-g0.tif", "bee3-g1.tif"):
        p = os.path.join(JUDGED_DIR, name)
        if os.path.exists(p):
            result["control_2347"].append(measure(p))

    for p in sorted(glob.glob(os.path.join(JUDGED_DIR, "ORCH-gallery", "*.tif")))[:3]:
        result["placebo_gallery"].append(measure(p))

    # Readings, applied mechanically to the pre-registered thresholds.
    j = result["judged"]
    result["readings"] = {
        "BINNING": (
            "CONFIRMED" if j and all(x["is_half_of_full_capture"] for x in j)
            else "REFUTED" if j else "NO DATA"
        ),
        "FLAT_TONE": (
            "CONFIRMED" if j and all(x["luma_p99_9_linear"] < 0.5 for x in j)
            else "REFUTED" if j else "NO DATA"
        ),
        "GREY_CAST": (
            "CONFIRMED" if j and all(
                x["green_over_red"] > 1.2 and x["green_over_blue"] > 1.2 for x in j
            ) else "REFUTED" if j else "NO DATA"
        ),
        "CONTROL_still_half_res": (
            "PASS" if result["control_2347"]
            and all(x["is_half_of_full_capture"] for x in result["control_2347"])
            else "FAIL" if result["control_2347"] else "NO DATA"
        ),
        "PLACEBO_gallery_not_dark": (
            "PASS" if result["placebo_gallery"]
            and all(x["luma_p99_9_linear"] >= 0.5 for x in result["placebo_gallery"])
            else "FAIL" if result["placebo_gallery"] else "NOT PRESENT"
        ),
    }

    dst = os.path.join(OUT, "05-judged-artefacts.json")

    # ------------------------------------------------------------------
    # DISCLOSURE. Three of the five readings above are MIS-SPECIFIED, and I
    # am recording that rather than editing the thresholds and pretending
    # otherwise. The pre-registered block is left exactly as it ran.
    #
    # BINNING: I compared all three judged files against ONE stack's full
    #   size (7032x4688). bee3 matches exactly; lavendar and marker are
    #   3520x2344, a different sensor crop, so the arm reported REFUTED for
    #   a reason that is not the hypothesis. The corrected arm asks whether
    #   each file is ~8.2 MP against a full-resolution render of the SAME
    #   stack where one is available.
    #
    # GREY_CAST: I predicted that "no colour management" would look like
    #   missing white balance, i.e. R and B depressed relative to G by the
    #   cam_wb ratios. Global channel MEANS cannot discriminate that from a
    #   correctly balanced image -- and the placebo proves it, because the
    #   colour-managed gallery render reads G/R = 1.0177 too. The arm
    #   returns NO EVIDENCE either way. I am not claiming fact 1344 is
    #   refuted on this point; I am saying my instrument could not see it.
    #
    # PLACEBO: I assumed every TIF under ORCH-gallery had been through the
    #   exposure post-process. The directory holds BOTH `-srgb` (raw output
    #   of the tool) and `-exposed` (post-processed) variants, so the arm
    #   swept in the uncorrected ones and failed by construction. Corrected
    #   below by splitting on the filename suffix. The accident was
    #   productive: see EXTERNAL_CHECK.
    # ------------------------------------------------------------------
    def is_binned(x):
        return 7.5 <= x["megapixels"] <= 9.0

    exposed = [x for x in result["placebo_gallery"] if x["file"].endswith("-exposed.tif")]
    raw_srgb = [x for x in result["placebo_gallery"] if x["file"].endswith("-srgb.tif")]

    result["readings_corrected"] = {
        "_disclosure": "Specified AFTER seeing the pre-registered arms fire. "
                       "Read the source comment above before trusting these.",
        "BINNING": (
            "CONFIRMED" if j and all(is_binned(x) for x in j) else "REFUTED"
        ),
        "BINNING_exact_for_bee3": (
            "CONFIRMED against a MEASURED full-res render of the same stack"
            if any(x["file"] == "bee3-full.tif" and x["width"] == 3516 for x in j)
            and any(x["width"] == 7032 and x["height"] == 4688 for x in raw_srgb)
            else "NOT ESTABLISHED"
        ),
        "FLAT_TONE": (
            "CONFIRMED for %d of %d judged files"
            % (sum(1 for x in j if x["stops_below_target_0_90"] > 1.0), len(j))
        ),
        "GREY_CAST": "NO EVIDENCE -- instrument cannot discriminate; see disclosure",
        "PLACEBO_exposed_not_dark": (
            "PASS" if exposed and all(x["stops_below_target_0_90"] < 0.5 for x in exposed)
            else "FAIL" if exposed else "NOT PRESENT"
        ),
        "CONTROL_still_half_res": result["readings"]["CONTROL_still_half_res"],
    }

    # The productive accident. `bee-3-cpl-srgb.tif` is the tool's own --srgb
    # output for the stack this milestone verifies, WITHOUT any exposure
    # correction. Measuring how far its p99.9 sits below 0.90 recomputes, in
    # numpy and from the emitted file, the quantity the shipped chooser
    # reports. If they agree, V2 stops resting on a prior report's printed
    # number and rests on an independent recomputation instead.
    bee_raw = next((x for x in raw_srgb if x["file"].startswith("bee-3-cpl")), None)
    if bee_raw is not None:
        result["EXTERNAL_CHECK"] = {
            "what": "independent numpy recomputation of the exposure deficit",
            "file": bee_raw["file"],
            "resolution": "%dx%d" % (bee_raw["width"], bee_raw["height"]),
            "numpy_stops_below_0_90": bee_raw["stops_below_target_0_90"],
            "shipped_chooser_prints": 1.54,
            "M100_published": 1.54,
            "delta_stops": round(abs(bee_raw["stops_below_target_0_90"] - 1.54), 4),
            "quantum_stops": 0.01,
            "reading": (
                "AGREES within the 1/100-stop quantum"
                if abs(bee_raw["stops_below_target_0_90"] - 1.54) <= 0.01
                else "DISAGREES"
            ),
        }

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result["readings"], indent=2))
    print(json.dumps(result["readings_corrected"], indent=2))
    print(json.dumps(result.get("EXTERNAL_CHECK", {}), indent=2))
    print("wrote " + dst)


if __name__ == "__main__":
    main()
