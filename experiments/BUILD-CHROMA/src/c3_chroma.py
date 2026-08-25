"""Edge chroma with a flat placebo: off vs shipped vs self-measured.

THE STATISTIC. Normalised chroma `(max - min) / max` over the three linear
channels, averaged over two pixel sets **frozen on the off arm** so that every
arm is judged on the same pixels:

    EDGE  top 1% of the luma gradient
    FLAT  bottom 50% of the luma gradient

FLAT is a built-in placebo rather than a separate experiment. A geometric
per-channel rescale can only move colour where there is structure to move, so it
must act on EDGE and must not act on FLAT. If both move, whatever moved them was
not the correction. Both numbers are reported raw beside the difference, in the
same table, because on at least one occasion in this project the raw statistic
and the excess-over-control disagreed in sign (rule 3).

THE FOUR ARMS.

    off          real render, STREHL_FIX_CA unset
    shipped      real render, STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl
    py-shipped   off render + a Python rescale using the SHIPPED coefficient
    py-self      off render + a Python rescale using the SELF-MEASURED coefficient

`py-shipped` exists only to validate `py-self`. I may not edit any `.rs` file, so
a self-measured coefficient cannot be fed to the renderer; it has to be applied
post hoc in Python, on the merged image. That is an approximation: the renderer
applies the correction per frame at gather time, before the merge elects a
winner, and post-hoc application commutes with the election only where the
elected index is constant over the ~1.5 px the correction moves. `py-shipped`
measures the size of that approximation directly, by running the SAME Python path
with the SAME coefficient the Rust arm used and asking whether it lands on the
same number. If it does not, `py-self` is not trustworthy and the report says so.
"""

import argparse
import os
import subprocess
import sys

import numpy as np
import tifffile
from scipy.ndimage import map_coordinates, sobel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

BIN = r"C:\dev\strehl-out\pin-5d7a7ba\target\release\strehl.exe"
REND = os.path.join(common.OUT, "render", "ca")
SHIPPED_KEY = "a7c2-fe100gm-2xtc-x4cpl"
SHIPPED_EPS_R = -704.5e-6
SHIPPED_EPS_B = None          # the record carries None: blue is an exact no-op
PPM = 1e6

# Linear-sRGB luma. The renders are made with --linear-srgb, which applies the
# camera matrix and stops before the transfer curve, so BT.709 weights are the
# right ones and the space is stated rather than implied.
LUMA = (0.2126, 0.7152, 0.0722)


def read16(path):
    """Read a 16-bit RGB TIFF. Rule 1: never PIL, and assert the dtype."""
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} shape {a.shape}"
    return a


def render(stack, arm, key=None):
    os.makedirs(REND, exist_ok=True)
    out = os.path.join(REND, f"{stack}-{arm}.tif")
    if os.path.exists(out):
        print(f"  [cached] {out}")
        return out
    env = dict(os.environ)
    if key:
        env["STREHL_FIX_CA"] = key
    else:
        env.pop("STREHL_FIX_CA", None)
    # --gate is mandatory with -o ("Requires exactly one --gate"); 2.0 is the
    # corpus-standard value M52 re-measured all seven stacks at.
    #
    # NOT --demosaic, deliberately. Malvar-He-Cutler interpolates colour from
    # neighbouring sites, which spatially mixes the channels at precisely the
    # high-gradient pixels the EDGE set selects -- it would both manufacture and
    # mask chroma there. The binned output is one real sensor quad per pixel,
    # R = R, G = (G1+G2)/2, B = B, with no spatial mixing at all, and it is the
    # same plane grid eps was measured on, so the coefficient needs no rescale.
    cmd = [BIN, "stack", os.path.join(common.LIB, stack), "-o", out,
           "--linear-srgb", "--gate", "2.0"]
    print(f"  rendering {arm}: STREHL_FIX_CA={key!r}")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit(f"render failed for {stack} {arm}")
    return out


def apply_eps(img, eps_r, eps_b, block=256):
    """Pull-resample R and B by (1 + eps) about the image centre.

    Matches `OpticalProfile::compose` exactly: `s = 1 + eps`, applied as a PULL,
    `dst(p) = src(s * p)` with `p` measured from the image centre. The doc
    comment on that function records that the inverse convention shipped once and
    made the aberration 7.2% worse, so the direction is written out here too
    rather than left to a reader.

    Blocked over rows because a full-resolution coordinate grid is 260 MB per
    axis and there are two of them per channel.
    """
    h, w, _ = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    out = img.astype(np.float32).copy()
    for k, e in ((0, eps_r), (2, eps_b)):
        if not e:
            continue
        s = 1.0 + e
        src = img[:, :, k].astype(np.float32)
        for y0 in range(0, h, block):
            y1 = min(y0 + block, h)
            yy, xx = np.mgrid[y0:y1, 0:w].astype(np.float64)
            sy = cy + s * (yy - cy)
            sx = cx + s * (xx - cx)
            out[y0:y1, :, k] = map_coordinates(
                src, [sy, sx], order=3, mode="nearest").astype(np.float32)
    return out


def masks(img):
    """EDGE and FLAT pixel sets, plus the gradient, computed on ONE arm."""
    a = img.astype(np.float32)
    y = LUMA[0] * a[:, :, 0] + LUMA[1] * a[:, :, 1] + LUMA[2] * a[:, :, 2]
    g = np.hypot(sobel(y, 0, mode="nearest"), sobel(y, 1, mode="nearest"))
    # Trim a border: the correction resamples with mode="nearest" and the
    # renderer's own alignment leaves edge pixels that are not comparable.
    m = np.zeros(g.shape, bool)
    b = 64
    m[b:-b, b:-b] = True
    gv = g[m]
    hi = np.quantile(gv, 0.99)
    lo = np.quantile(gv, 0.50)
    return (m & (g >= hi)), (m & (g <= lo)), g


def chroma(img):
    """Normalised chroma per pixel: (max - min) / max over the linear channels."""
    a = img.astype(np.float32)
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)


def score(img, edge, flat):
    c = chroma(img)
    return float(c[edge].mean()), float(c[flat].mean())


def run(stack, eps_r_self, eps_b_self, recovery=None):
    print(f"\n=== {stack} ===")
    off_p = render(stack, "off", None)
    on_p = render(stack, "shipped", SHIPPED_KEY)
    off = read16(off_p)
    on = read16(on_p)
    assert off.shape == on.shape, f"{off.shape} vs {on.shape}"
    print(f"  render shape {off.shape}")

    edge, flat, g = masks(off)
    print(f"  EDGE {edge.sum():,} px   FLAT {flat.sum():,} px "
          f"(frozen on the off arm)")

    arms = {}
    arms["off"] = score(off, edge, flat)
    arms["shipped (rust)"] = score(on, edge, flat)
    del on
    py_ship = apply_eps(off, SHIPPED_EPS_R, 0.0)
    arms["shipped (python)"] = score(py_ship, edge, flat)
    del py_ship
    py_self = apply_eps(off, eps_r_self, eps_b_self)
    arms["self (python)"] = score(py_self, edge, flat)
    del py_self
    py_self_r = apply_eps(off, eps_r_self, 0.0)
    arms["self R only (python)"] = score(py_self_r, edge, flat)
    del py_self_r
    py_self_b = apply_eps(off, 0.0, eps_b_self)
    arms["self B only (python)"] = score(py_self_b, edge, flat)
    del py_self_b
    if recovery:
        # c4 established that the estimator is attenuated by a stack-dependent
        # factor (planted +1000 ppm read back at 0.69-0.94). Dividing the raw
        # coefficient by the measured recovery is the de-attenuated estimate;
        # this arm asks whether de-attenuation helps the picture or overshoots.
        py_att = apply_eps(off, eps_r_self / recovery, eps_b_self / recovery)
        arms[f"self/atten {recovery:.3f} (python)"] = score(py_att, edge, flat)
        del py_att

    e0, f0 = arms["off"]
    print(f"\n  {'arm':>22} {'EDGE':>10} {'dEDGE':>9} {'FLAT':>10} {'dFLAT':>9} {'ratio':>7}")
    rows = []
    for k, (e, f) in arms.items():
        de = 100.0 * (e - e0) / e0
        df = 100.0 * (f - f0) / f0
        ratio = abs(de / df) if abs(df) > 1e-9 else float("inf")
        print(f"  {k:>22} {e:10.6f} {de:8.2f}% {f:10.6f} {df:8.2f}% "
              f"{ratio:7.1f}")
        rows.append({"arm": k, "edge": e, "flat": f, "d_edge_pct": de,
                     "d_flat_pct": df, "edge_over_flat": ratio})

    # The emulation check: does the Python path reproduce the Rust path when
    # given the same coefficient? Recovery is the fraction of the Rust arm's
    # movement that the post-hoc Python path reproduces. It is below 1 because
    # Rust applies the correction per frame BEFORE the election and Python
    # applies it once to the merged image; the two commute only where the
    # elected index is constant over the ~1.5 px the correction moves.
    er = arms["shipped (rust)"][0]
    ep = arms["shipped (python)"][0]
    agree = 100.0 * (ep - e0) / (er - e0) if abs(er - e0) > 1e-12 else float("nan")
    print(f"\n  emulation check: rust dEDGE {100*(er-e0)/e0:+.3f}%, "
          f"python dEDGE {100*(ep-e0)/e0:+.3f}%  -> python reproduces "
          f"{agree:.1f}% of the rust effect")

    return {"stack": stack, "shape": list(off.shape),
            "n_edge": int(edge.sum()), "n_flat": int(flat.sum()),
            "eps_r_self": eps_r_self, "eps_b_self": eps_b_self,
            "arms": rows, "emulation_recovery_pct": agree}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stacks", nargs="+")
    a = ap.parse_args()
    res = []
    import json
    recov = {}
    try:
        with open(os.path.join(common.OUT, "json",
                               "c4_attenuation.json")) as fh:
            for r in json.load(fh)["dose"]:
                recov[r["stack"]] = r["recovery"]
    except (OSError, KeyError) as e:
        print(f"note: no c4 recovery table ({e}); skipping the de-attenuated arm")
    for st in a.stacks:
        with open(os.path.join(common.OUT, "json",
                               f"c1_lateral_{st}.json")) as fh:
            j = json.load(fh)
        h = j["headline"]
        res.append(run(st, h["R"]["eps_null_corrected"],
                       h["B"]["eps_null_corrected"], recov.get(st)))
    common.dump("c3_chroma", res)
    print("\nwrote c3_chroma.json")
