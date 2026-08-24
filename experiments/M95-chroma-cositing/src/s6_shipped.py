"""S6 — measure the shipped renders end to end, and build the deliverable figure.

Everything up to here measured a Python simulation of the correction. This
measures the two TIFFs the two binaries actually wrote, on the configuration
that ships: alignment on, `--gate 2.0`, `--srgb`.

CROP SELECTION IS BLIND TO THE EFFECT
-------------------------------------
The crop for the figure is chosen by green-channel gradient energy alone. Green
is the one channel the fix does not touch, so the selection cannot see the
result and cannot be steered by it. Picking the crop where the fix helped most
would have been a cherry-pick; picking it where the picture has the strongest
edges is the fair criterion, and it is also where a viewer looks.

CONTROLS
--------
did-anything  the fix must have changed red and blue at all.
N2-corrected  the "green is untouched" claim is NOT checkable on this path: the
              matrix mixes channels, so output green must move. See the note in
              the code and `s9_camera_linear_null.py`.
N5-null       the same registration metric run on the reference against ITSELF
              must read ~0. A metric that reads a non-zero offset between a file
              and itself is measuring its own arithmetic.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402
from s4_benefit import box2, chroma_error, field_rois, registration  # noqa: E402

OUT = r"C:\dev\strehl-out\M95-chroma-cositing"
S = 256


def load(name):
    import tifffile

    return tifffile.imread(os.path.join(OUT, name)).astype(np.float64)


def main():
    res = {}
    print("== loading the two shipped renders and the demosaic reference ==")
    before = load("ship-before.tif")
    after = load("ship-after.tif")
    demo = load("ship-demosaic.tif")
    print("   binned %s   demosaic %s" % (before.shape, demo.shape))

    # ---------------------------------------------------------- N2-shipped
    #
    # NOTE, and it is a correction to this file's first version. This control
    # originally demanded that OUTPUT green be bit-identical between the two
    # renders. It failed, and it was wrong to ask: `--srgb` puts the camera
    # matrix in the path, and that matrix mixes channels, so changing red and
    # blue MUST change output green. The claim "green is untouched" is about
    # the input to development, and it is checked two ways instead:
    #
    #   * bit-exactly, with no matrix, by the Rust unit test
    #     `the_binned_path_leaves_green_untouched_and_separates_red_from_blue`,
    #     certified by mutation control R2;
    #   * at shipped scale in `s9_camera_linear_null.py`, which inverts the
    #     curve and the matrix and finds green 738x quieter than chroma.
    #
    # What remains here is the weaker but still necessary check: the fix did
    # something to red and blue, and did not silently do nothing.
    dr = int(np.abs(before[:, :, 0] - after[:, :, 0]).max())
    db = int(np.abs(before[:, :, 2] - after[:, :, 2]).max())
    print("\n== the fix changed red and blue (a did-anything-happen check) ==")
    print("   max |dR| %d DN, max |dB| %d DN" % (dr, db))
    print("   green identity is checked without a matrix, in the Rust unit test,")
    print("   and in camera-linear space in s9_camera_linear_null.py -- see the note above.")
    n2 = dr > 0 and db > 0
    print("   changed: %s" % ("PASS" if n2 else "FAIL"))
    res["did_anything_happen"] = {"max_dR_DN": dr, "max_dB_DN": db, "pass": n2}

    ground = np.stack([box2(demo[:, :, c]) for c in range(3)], axis=2)
    h, w = before.shape[0], before.shape[1]
    rois = field_rois(h, w, S, nx=7, ny=5)

    # ---------------------------------------------------------------- N5
    print("\n== N5-null: the reference against itself ==")
    null = registration(ground, ground, rois)
    print("   R %.5f  G %.5f  B %.5f px" % (null["R"], null["G"], null["B"]))
    n5 = max(null.values()) < 0.01
    print("   N5: %s (bar < 0.01 px)" % ("PASS" if n5 else "FAIL"))
    res["N5_null"] = {**{k: float(v) for k, v in null.items()}, "pass": bool(n5)}

    # ------------------------------------------------------ the measurement
    print("\n== end-to-end on the shipped renders ==")
    for tag, img in (("before", before), ("after", after)):
        reg = registration(ground, img, rois)
        ca, ce = chroma_error(ground, img, rois)
        res[tag] = {"reg_R": reg["R"], "reg_G": reg["G"], "reg_B": reg["B"],
                    "chroma_rms_DN": ca, "chroma_rms_edge_DN": ce}
        print("   %-7s regR %.4f  regG %.4f  regB %.4f   chroma %8.1f DN   edge %8.1f DN"
              % (tag, reg["R"], reg["G"], reg["B"], ca, ce))
    b, a = res["before"], res["after"]
    print("\n   red  misregistration  %.4f -> %.4f binned px  (%.1f%% removed)"
          % (b["reg_R"], a["reg_R"], 100 * (1 - a["reg_R"] / b["reg_R"])))
    print("   blue misregistration  %.4f -> %.4f binned px  (%.1f%% removed)"
          % (b["reg_B"], a["reg_B"], 100 * (1 - a["reg_B"] / b["reg_B"])))
    print("   chroma RMS at edges   %.1f -> %.1f DN  (%.1f%% lower)"
          % (b["chroma_rms_edge_DN"], a["chroma_rms_edge_DN"],
             100 * (1 - a["chroma_rms_edge_DN"] / b["chroma_rms_edge_DN"])))

    # ------------------------------------------------------------- figure
    print("\n== choosing the figure crop, using GREEN ONLY ==")
    g = before[:, :, 1]
    cs = 220
    best, bxy = -1.0, (0, 0)
    for y in range(200, h - cs - 200, 90):
        for x in range(200, w - cs - 200, 90):
            t = g[y:y + cs, x:x + cs]
            gy, gx = np.gradient(t)
            e = float(np.mean(np.hypot(gy, gx)))
            if e > best:
                best, bxy = e, (y, x)
    y, x = bxy
    print("   crop at (%d, %d) size %d, green gradient energy %.1f DN/px" % (y, x, cs, best))
    res["crop"] = {"y": int(y), "x": int(x), "size": cs, "green_grad_DN_per_px": best}

    cb = before[y:y + cs, x:x + cs, :]
    ca_ = after[y:y + cs, x:x + cs, :]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def show(t):
        v = t / 65535.0
        lo, hi = np.percentile(v, 1.0), np.percentile(v, 99.5)
        return np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)

    def chroma_vis(t, gain=6.0):
        v = t / 65535.0
        out = np.full_like(v, 0.5)
        out[:, :, 0] = 0.5 + gain * (v[:, :, 0] - v[:, :, 1])
        out[:, :, 2] = 0.5 + gain * (v[:, :, 2] - v[:, :, 1])
        return np.clip(out, 0, 1)

    fig, ax = plt.subplots(2, 2, figsize=(11.0, 11.6))
    fig.patch.set_facecolor("white")
    panels = [
        (0, 0, show(cb), "A  BEFORE - as shipped", 
         "red and blue written as if co-sited with green"),
        (0, 1, show(ca_), "B  AFTER - chroma co-sited",
         "red resampled +0.25 px, blue -0.25 px, green untouched"),
        (1, 0, chroma_vis(cb), "C  BEFORE, chroma only (6x)",
         "luminance removed; colour swing at edges is the fringe"),
        (1, 1, chroma_vis(ca_), "D  AFTER, chroma only (6x)",
         "same crop, same gain, same stretch"),
    ]
    for r, c, im, t1, t2 in panels:
        a_ = ax[r][c]
        a_.imshow(im, interpolation="nearest")
        a_.set_xticks([])
        a_.set_yticks([])
        a_.set_title(t1, fontsize=11, loc="left", fontweight="bold")
        a_.set_xlabel(t2, fontsize=8.5)

    fig.suptitle(
        "M95 - chroma co-siting on the binned sRGB render\n"
        "strehl stack bee-3-cpl --gate 2.0 --srgb   |   crop chosen by GREEN gradient only, "
        "blind to the effect",
        fontsize=11.5, y=0.975,
    )
    fig.text(
        0.5, 0.018,
        "Measured over the whole frame, not this crop: red channel misregistration against the "
        "demosaiced reference\n"
        "%.3f -> %.3f binned px, blue %.3f -> %.3f. Green is unchanged as an input; its\n"
        "output moves only because the colour matrix mixes channels (s9: 738x quieter than chroma).\n"
        "No sharpness number is claimed on these panels; luminance sharpness was not measured on this axis."
        % (b["reg_R"], a["reg_R"], b["reg_B"], a["reg_B"]),
        ha="center", fontsize=8.5, color="0.25",
    )
    fig.tight_layout(rect=[0, 0.055, 1, 0.945])
    path = os.path.join(OUT, "M95-chroma-cositing-before-after.png")
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    print("   wrote %s" % path)
    res["figure"] = path

    C.jdump("s6_shipped.json", res)
    ok = n2 and n5 and a["reg_R"] < b["reg_R"] and a["reg_B"] < b["reg_B"]
    print("\nS6: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
