"""V4's positive control and V6's percentile-tail question, from the emitted TIFs.

V4 positive control
    `--exposure=1.00` must be exactly 2.0x `--exposure 0` in LINEAR light.
    The files are sRGB-encoded 16-bit, so both are linearised first. Only the
    population that is unclipped in BOTH files can carry the ratio: a pixel at
    65535 in the brighter file has lost the information.

    Rule 34: the constant 2.0 comes from the definition of a stop, not from
    `color.rs`. This control shares no constant with the code it tests.

V6  Is p99.9 riding a specular tail?
    Reports p99.9, p99.99 and the max of linear-sRGB luminance, and the ratios
    between them, on an insect stack and on two stacks with no large specular.

Read-only on D:. Reads only files already written under C:\\dev\\strehl-out.
"""

import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M105"

# BT.709 luminance, the same weighting `color::luminance` uses.
LUMA = np.array([0.212_636, 0.715_183, 0.072_192], dtype=np.float64)


def srgb_to_linear(x):
    """The exact inverse of `color::srgb_encode`, on [0, 1] floats."""
    return np.where(x <= 0.040_45, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def load_linear(path):
    a = tifffile.imread(path)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16" % (path, a.dtype))
    return srgb_to_linear(a.astype(np.float64) / 65535.0), a


def v4_positive_control():
    lin0, raw0 = load_linear(os.path.join(OUT, "v4-exp0-299.tif"))
    lin1, raw1 = load_linear(os.path.join(OUT, "v4-exp1-299.tif"))
    if lin0.shape != lin1.shape:
        raise SystemExit("shape mismatch %s vs %s" % (lin0.shape, lin1.shape))

    # Unclipped in both, and above the sRGB toe where 16-bit quantisation of the
    # encoded value is coarse relative to the linear value it represents.
    ok = (raw1 < 65535) & (raw0 > 2048) & (lin0 > 0)
    ratio = (lin1[ok] / lin0[ok]).ravel()

    q = np.percentile(ratio, [25, 50, 75])
    return {
        "n_pixels_total": int(lin0.size),
        "n_pixels_used": int(ratio.size),
        "frac_used": float(ratio.size) / float(lin0.size),
        "ratio_median": float(q[1]),
        "ratio_p25": float(q[0]),
        "ratio_p75": float(q[2]),
        "ratio_iqr": float(q[2] - q[0]),
        "ratio_mean": float(ratio.mean()),
        "expected": 2.0,
        "median_rel_error": float(abs(q[1] - 2.0) / 2.0),
        # PASS needs the median within 0.5% of 2.000 AND the IQR below 0.01.
        "V4_positive_pass": bool(abs(q[1] - 2.0) / 2.0 < 0.005 and (q[2] - q[0]) < 0.01),
        # The placebo, restated from the hashes so both arms sit in one artifact.
        "placebo_note": "see 01-render.json: v4-plain-299 and v4-exp0-299 SHA-256",
    }


def v6_tail(name, path):
    if not os.path.exists(path):
        return {"stack": name, "status": "not rendered"}
    lin, _ = load_linear(path)
    y = (lin * LUMA).sum(axis=2).ravel()
    p995, p999, p9999 = np.percentile(y, [99.5, 99.9, 99.99])
    mx = float(y.max())
    return {
        "stack": name,
        "p99_5": float(p995),
        "p99_9": float(p999),
        "p99_99": float(p9999),
        "max": mx,
        "p9999_over_p999": float(p9999 / p999) if p999 > 0 else None,
        "max_over_p999": float(mx / p999) if p999 > 0 else None,
        "p999_over_p995": float(p999 / p995) if p995 > 0 else None,
        "n_above_p999": int((y > p999).sum()),
        # SUBSTANTIATED if the top 0.1% is a steep tail p99.9 is riding.
        "V6_specular_substantiated": bool(p999 > 0 and (p9999 / p999) >= 1.15),
    }


def main():
    res = {"V4_positive_control": v4_positive_control(), "V6_tail": []}
    for name in sys.argv[1:]:
        res["V6_tail"].append(v6_tail(name, os.path.join(OUT, "v6-%s.tif" % name)))
    # The already-rendered bee arm, un-exposed so the tail is the capture's own.
    res["V6_tail"].insert(0, v6_tail("bee-3-cpl", os.path.join(OUT, "v4-exp0-299.tif")))
    print(json.dumps(res, indent=2))
    with open(os.path.join(OUT, "02-analyse.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
