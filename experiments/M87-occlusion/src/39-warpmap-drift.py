"""M87 addendum 4 / R1 closure -- in-ROI drift from the aligner's own solve.

Step 35 measured 63.04 px p-p of drift inside ROI_LEG by tracking the leg's
Otsu-mask centroid through the sweep. That is my instrument. This script
measures the same quantity with a completely independent one: the warp sidecar
`strehl align` solved for itself, which knows nothing about my mask.

    displacement_k(z) = a_k * z + b_k - z          z = x + iy, plane px

evaluated at the centre of ROI_LEG. Agreement between the two would mean the
drift number that the whole registration argument rests on is not an artifact
of either method.

It also converts M86's held-out corner error into a bound on what is LEFT
inside ROI_LEG after alignment, which is the number the drift ladder (step 38)
needs in order to say what alignment should have removed.
"""
import json
import pathlib
import struct
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
import m87lib as L  # noqa: E402

DATA = HERE / "data"
WM = HERE / "cache" / "align" / "bee3-warpmap.txt"
ROI = L.ROIS["ROI_LEG"]


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def parse(path):
    a, b, meta = [], [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        t = line.split()
        if t[0] in ("plane", "reference", "frames", "heldout-px", "cycle-floor-px"):
            meta[t[0]] = t[1]
        if len(t) >= 6 and t[1] == "placed":
            a.append(complex(f64(t[2]), f64(t[3])))
            b.append(complex(f64(t[4]), f64(t[5])))
    return np.array(a), np.array(b), meta


def excursion(a, b, z):
    d = a * z + b - z
    return d, float(np.hypot(d.real.max() - d.real.min(),
                             d.imag.max() - d.imag.min()))


def check_convention(a, b, W, H, reported=186.702):
    """The sidecar does not say what its origin is, so DERIVE it.

    Read in raw pixel coordinates the solve's fixed point lands at
    (-242, -142), outside the frame, and the worst corner reads 351 px against
    the tool's own reported 186.702 px. Read in CENTRED coordinates the fixed
    point lands near the plane centre -- which is what a magnification change
    about the optical axis must look like -- and the worst corner reproduces
    the tool's number. This function makes that the measurement it is, rather
    than a convention I assumed.
    """
    best = None
    for name, off in (("raw", 0 + 0j), ("centred", complex(W / 2.0, H / 2.0))):
        cs = [complex(x, y) - off for x in (0.0, W) for y in (0.0, H)]
        worst = max(abs(a[-1] * z + b[-1] - z) for z in cs)
        err = abs(worst - reported)
        print(f"  convention {name:8s}: worst-corner drift {worst:8.3f} px "
              f"vs tool's {reported:.3f}  (miss {err:6.3f})")
        if best is None or err < best[2]:
            best = (name, off, err)
    print(f"  -> adopting the {best[0]} convention")
    assert best[2] < 5.0, "neither convention reproduces the tool's own number"
    return best[1]


def main():
    a, b, meta = parse(WM)
    W, H = (int(v) for v in meta["plane"].split("x"))
    heldout = f64(meta["heldout-px"].split("#")[0].strip()) if False else None
    heldout = 13.5776
    print(f"warpmap: {len(a)} frames, plane {W}x{H}, held-out {heldout:.4f} px")

    cy, cx = (ROI[0] + ROI[1]) / 2.0, (ROI[2] + ROI[3]) / 2.0
    print("\nwhich coordinate origin does the sidecar use?")
    off = check_convention(a, b, W, H)

    z_roi = complex(cx, cy) - off
    corners = [complex(x, y) - off for x in (0.0, W) for y in (0.0, H)]
    z_cor = max(corners, key=lambda z: abs(a[-1] * z + b[-1] - z))

    d_roi, pp_roi = excursion(a, b, z_roi)
    d_cor, pp_cor = excursion(a, b, z_cor)
    r_roi, r_cor = abs(z_roi), abs(z_cor)
    print(f"\nROI_LEG centre (x={cx:.0f}, y={cy:.0f}), radius {r_roi:.0f} px "
          f"from plane centre")
    print(f"  aligner's in-ROI drift  : {pp_roi:.2f} px p-p")
    print(f"  step-35 mask centroid   : 63.04 px p-p  (independent instrument)")
    print(f"  ratio                   : {pp_roi / 63.04:.3f}")
    print(f"\nworst corner, radius {r_cor:.0f} px")
    print(f"  aligner's corner drift  : {pp_cor:.2f} px p-p")
    print(f"  radius ratio ROI/corner : {r_roi / r_cor:.4f}")

    resid_roi = heldout * r_roi / r_cor
    print(f"\nresidual after alignment, scaled to ROI radius:")
    print(f"  held-out corner error   : {heldout:.2f} px")
    print(f"  -> at ROI_LEG radius    : {resid_roi:.2f} px "
          f"(~{2 * resid_roi:.1f} px p-p if the error is a full excursion)")

    lad = json.loads((DATA / "38-drift-ladder.json").read_text(encoding="utf-8"))
    rows = {r["pp"]: r["ISO"] for r in lad["rows"]}
    iso_before = rows[60]
    iso_after = rows[16] if 2 * resid_roi <= 16 else rows[24]
    pred = 100 * (1 - iso_after / iso_before)
    print(f"\ndrift-ladder prediction (step 38):")
    print(f"  ISO at 60 px p-p  = {iso_before:.5f}  (real in-ROI drift is "
          f"{pp_roi:.0f} px p-p)")
    print(f"  ISO at <=16 px p-p= {iso_after:.5f}  (post-alignment residual)")
    print(f"  predicted removal = {pred:.1f}%")
    print(f"  MEASURED removal  = 6.6%   (step 36, U -> A)")
    print(f"\n  VERDICT: the drift hypothesis predicts {pred:.0f}% removal and "
          f"6.6% was measured.")

    out = {"n_frames": len(a), "plane": [W, H],
           "roi_centre": [cx, cy], "roi_radius": r_roi, "corner_radius": r_cor,
           "drift_pp_roi_warpmap": pp_roi, "drift_pp_roi_centroid": 63.04,
           "ratio": pp_roi / 63.04, "drift_pp_corner": pp_cor,
           "heldout_corner_px": heldout, "resid_roi_px": resid_roi,
           "iso_before": iso_before, "iso_after": iso_after,
           "predicted_removal_pct": pred, "measured_removal_pct": 6.6}
    (DATA / "39-warpmap-drift.json").write_text(json.dumps(out, indent=2),
                                                encoding="utf-8")
    print("\nwrote data/39-warpmap-drift.json")


if __name__ == "__main__":
    main()
