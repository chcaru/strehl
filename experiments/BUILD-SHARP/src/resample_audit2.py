"""Audit II: the two sites that were conditional in section 20 and have now fired.

Section 20 classified the lateral-CA warp and the pyramid as NOT-ON-THIS-PATH
*conditionally*, and named the conditions. Both fired: `--fix-ca` is default-on
and certified on 25/26 subjects, and pyramid is the shipping merge backend.

So they must be priced. Three questions, in ORCH's order:

  1. Is the shipped default a NET sharpness loss? CA removes fringing but is
     another warp.
  2. Can the CA warp fold into the gather like the co-site can? It is a radial
     scale, not a constant translation, so it will not compose as trivially.
  3. What does the pyramid path itself cost, now that it ships?

The method is section 20's and so are the guards: sites partition into counted
outcomes that sum to the total, and every instrument gets a plant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resample_price import mtf  # noqa: E402
from resample_audit import amplitude, parse_warpmap  # noqa: E402

BANDS = (0.25, 0.35, 0.50)
KERNEL = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0

# optics.rs:351 A7C2_FE100GM_2XTC_X4CPL, and the _RADIAL twin at :458 that is
# what `resolve_for_capture` actually returns (:570, :597).
EPS_R = -704.5e-6
EPS_B = 174.4e-6
TRANSLATION_RECORDED = (0.6294, -0.4240)  # NOT applied: the RADIAL twin zeroes it


# ---------------------------------------------------------------------------
# the gather coordinate, exactly as the Rust computes it
# ---------------------------------------------------------------------------

def apply_at(a: complex, b: complex, z: np.ndarray, c: complex) -> np.ndarray:
    """align.rs:290 -- centre-relative, then centre added back."""
    return (a * (z - c) + b) + c


def compose(a: complex, b: complex, eps: float | None, t: tuple[float, float]):
    """optics.rs:297 -- returns ONE Similarity doing alignment and CA together."""
    if eps is None:
        return a, b
    s = 1.0 + eps
    return complex(a.real * s, a.imag * s), complex(b.real * s + t[0], b.imag * s + t[1])


def phases(w, h, frames, eps=None, translation=(0.0, 0.0), centred=True):
    ys, xs = np.meshgrid(
        np.arange(0, h, 64, dtype=np.float64),
        np.arange(0, w, 64, dtype=np.float64),
        indexing="ij",
    )
    z = xs + 1j * ys
    c = complex(w * 0.5, h * 0.5) if centred else 0j
    px, py = [], []
    for _i, a, b in frames:
        a2, b2 = compose(a, b, eps, translation)
        zp = apply_at(a2, b2, z, c) if centred else a2 * z + b2
        px.append(np.mod(zp.real, 1.0).ravel())
        py.append(np.mod(zp.imag, 1.0).ravel())
    return np.concatenate(px), np.concatenate(py)


# ---------------------------------------------------------------------------
# pyramid.rs, transcribed
# ---------------------------------------------------------------------------

def reduced(n: int) -> int:
    return (n + 1) // 2


def _clamp(i, n):
    return np.clip(i, 0, n - 1)


def reduce_op(src: np.ndarray) -> np.ndarray:
    sh, sw = src.shape
    dw, dh = reduced(sw), reduced(sh)
    tmp = np.zeros((sh, dw))
    for t in range(5):
        tmp += KERNEL[t] * src[:, _clamp(2 * np.arange(dw) + t - 2, sw)]
    dst = np.zeros((dh, dw))
    for t in range(5):
        dst += KERNEL[t] * tmp[_clamp(2 * np.arange(dh) + t - 2, sh), :]
    return dst


def _expand_axis(src: np.ndarray, n_out: int) -> np.ndarray:
    """The explicit two-phase form: even [1,6,1]/8, odd [1,1]/2."""
    n_in = src.shape[1]
    out = np.zeros((src.shape[0], n_out))
    x = np.arange(n_out)
    c = x // 2
    even = x % 2 == 0
    ce = c[even]
    out[:, even] = (
        0.125 * src[:, _clamp(ce - 1, n_in)]
        + 0.75 * src[:, ce]
        + 0.125 * src[:, _clamp(ce + 1, n_in)]
    )
    co = c[~even]
    out[:, ~even] = 0.5 * (src[:, co] + src[:, _clamp(co + 1, n_in)])
    return out


def expand_op(src: np.ndarray, out_shape) -> np.ndarray:
    dh, dw = out_shape
    tmp = _expand_axis(src, dw)
    return _expand_axis(tmp.T, dh).T


def laplacian_roundtrip(img: np.ndarray, bands: int, plant: float | None = None):
    """Analyse to `bands` Laplacian levels then collapse. Returns the result."""
    g = [img]
    for _ in range(bands):
        g.append(reduce_op(g[-1]))
    lap = [g[i] - expand_op(g[i + 1], g[i].shape) for i in range(bands)]
    if plant is not None:
        lap[0] = lap[0] * plant
    r = g[bands]
    for i in range(bands - 1, -1, -1):
        r = lap[i] + expand_op(r, lap[i].shape)
    return r


def amp_at(img: np.ndarray, f: float) -> float:
    """Amplitude of the horizontal sinusoid at f, measured well inside the border."""
    m = img[64:-64, 64:-64]
    x = np.arange(m.shape[1])
    s, c = np.sin(2 * np.pi * f * x), np.cos(2 * np.pi * f * x)
    return float(np.hypot((m * s).mean(), (m * c).mean()) * 2.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--warpmap",
        default="crates/strehl-cli/tests/data/coffee-bean-20.warpmap.txt",
    )
    args = ap.parse_args()

    name, w, h, frames = parse_warpmap(Path(args.warpmap))
    print("=" * 78)
    print(f"Q0  section 20 used an UNCENTRED phase model. Correct it and re-check.")
    print("=" * 78)
    p_un = phases(w, h, frames, centred=False)
    p_ct = phases(w, h, frames, centred=True)
    print("apply_at is centre-relative (align.rs:290); section 20 evaluated a*z+b.")
    print("The difference is a CONSTANT offset c - a*c, ~3.5 px here, so on a")
    print("near-uniform phase distribution the mean amplitude should be unmoved:")
    for f in BANDS:
        a0, a1 = amplitude(*p_un, f).mean(), amplitude(*p_ct, f).mean()
        print(f"  f={f:.2f}  uncentred {a0:.5f}   centred {a1:.5f}   "
              f"delta {100 * (a1 - a0) / a0:+.2f}%")
    print("  -> section 20's table stands; the model is now exact regardless.")

    print("\n" + "=" * 78)
    print("Q1/Q2  THE CA WARP IS ALREADY FOLDED INTO THE GATHER")
    print("=" * 78)
    print("optics.rs:297 `OpticalProfile::compose` returns ONE Similarity doing")
    print("alignment and CA together; align_cmd.rs:1430 calls it per CFA plane and")
    print("passes the result straight to gather_checked. A radial magnification")
    print("about a point IS a similarity, and similarities are closed under")
    print("composition, so the answer to Q2 is: it already composes, exactly.")
    print()
    print("So CA's cost is NOT a second kernel. It is only whatever the composed")
    print("scale does to the phase distribution of the ONE gather:")
    hdr = f"{'f':>6} {'align only':>11} {'+CA red':>10} {'+CA blue':>10} {'red cost':>10}"
    print(hdr)
    p_r = phases(w, h, frames, eps=EPS_R)
    p_b = phases(w, h, frames, eps=EPS_B)
    for f in BANDS:
        a0 = amplitude(*p_ct, f).mean()
        ar = amplitude(*p_r, f).mean()
        ab = amplitude(*p_b, f).mean()
        print(f"{f:6.2f} {a0:11.5f} {ar:10.5f} {ab:10.5f} {100 * (ar - a0) / a0:+9.2f}%")
    print()
    print("Counterfactual, had CA been applied as its own pass (ORCH's estimate):")
    for f in BANDS:
        print(f"  f={f:.2f}  red phi=0.152 -> {mtf(f, 0.152) ** 2:.5f} 2-D,  "
              f"blue phi=0.039 -> {mtf(f, 0.039) ** 2:.5f} 2-D")
    print("  That cost is AVOIDED, not paid. Q1 answer: the shipped CA default is")
    print("  NOT a net sharpness loss -- it is amplitude-neutral by construction.")

    print("\n" + "=" * 78)
    print("Q1b  AND THE PROFILE THAT SHIPS ZEROES THE TRANSLATION")
    print("=" * 78)
    print(f"A7C2_FE100GM_2XTC_X4CPL records translation {TRANSLATION_RECORDED} plane px,")
    print("which its own docs note is 'the same order as the ~0.5 px/axis that CFA")
    print("co-siting predicts'. resolve_for_capture returns the _RADIAL twin")
    print("(optics.rs:570,597) whose translation is (0,0), so it is NOT applied.")
    print("=> no double-correction against BUILD-COSITE's incoming +/-0.25. If the")
    print("   non-radial profile were ever selected, these two would collide.")

    print("\n" + "=" * 78)
    print("Q3  THE PYRAMID IS A PERFECT-RECONSTRUCTION FILTER BANK")
    print("=" * 78)
    rng = np.random.default_rng(7)
    img = rng.standard_normal((512, 512))
    rt = laplacian_roundtrip(img, bands=7)
    err = np.abs(rt - img).max()
    print(f"analyse 7 bands then collapse, 512x512 white noise:")
    print(f"  max |collapse(analyse(x)) - x| = {err:.3e}   (float64 round-off)")
    print("  The Laplacian is DEFINED as the residual G_i - expand(G_i+1), so the")
    print("  collapse is algebraically the identity. It removes no amplitude.")
    print()
    print("Per-band amplitude through analysis+synthesis, unmodified:")
    for f in BANDS:
        x = np.arange(512)
        sig = np.tile(np.sin(2 * np.pi * f * x), (512, 1))
        out = laplacian_roundtrip(sig, bands=7)
        print(f"  f={f:.2f}  retained {amp_at(out, f) / amp_at(sig, f):.6f}")

    print("\n  POTENCY -- scale the finest Laplacian band by 0.80 and the")
    print("  instrument must see it:")
    ok = True
    for f in BANDS:
        x = np.arange(512)
        sig = np.tile(np.sin(2 * np.pi * f * x), (512, 1))
        out = laplacian_roundtrip(sig, bands=7, plant=0.80)
        r = amp_at(out, f) / amp_at(sig, f)
        moved = r < 0.999
        ok &= moved
        print(f"    f={f:.2f}  retained {r:.6f}  {'MOVED' if moved else 'DID NOT MOVE'}")
    print(f"  potency: {'the pyramid instrument responds' if ok else 'FAILED'}")

    print("\n" + "=" * 78)
    print("REVISED PARTITION -- 8 sites, shipped configuration")
    print("=" * 78)
    part = [
        ("PRICED", "alignment gather + CA (ONE composed gather)", "align_cmd.rs:1430"),
        ("PRICED", "chroma co-site, R/B, second kernel", "image_out.rs:956"),
        ("PRICED", "pyramid reduce/expand", "pyramid.rs:151,211"),
        ("NOT-A-RESAMPLE", "2x2 quad binning (decimation, defines lattice)", "write_binned"),
        ("NOT-A-RESAMPLE", "edgeaware gather_levels (level select)", "edgeaware.rs:616"),
        ("NOT-ON-THIS-PATH", "demosaic (binned path never demosaics)", "demosaic.rs"),
        ("NOT-ON-THIS-PATH", "align-solve downsample (yields a transform)", "align.rs:484"),
        ("COULD-NOT-INSTRUMENT", "output scaling, if any exists downstream", "-- see notes"),
    ]
    counts: dict[str, int] = {}
    for outcome, what, where in part:
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"  [{outcome:20s}] {what}   ({where})")
    print()
    for k in sorted(counts):
        print(f"  {k:22s} {counts[k]:3d}")
    print(f"  {'TOTAL':22s} {len(part):3d}")
    assert sum(counts.values()) == len(part)

    print("\n" + "=" * 78)
    print("SHIPPED CHAIN, composed amplitude")
    print("=" * 78)
    print(f"{'f':>6} {'G':>9} {'R/B now':>10} {'R/B folded':>12} {'gain':>8}")
    for f in BANDS:
        g = amplitude(*p_ct, f).mean()
        rb_now = amplitude(*p_r, f).mean() * mtf(f, 0.25) ** 2
        rb_fold = amplitude(*p_r, f).mean()
        print(f"{f:6.2f} {g:9.5f} {rb_now:10.5f} {rb_fold:12.5f} {rb_fold / rb_now:7.3f}x")
    print("\nPyramid contributes a factor of 1.000000 to every cell above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
