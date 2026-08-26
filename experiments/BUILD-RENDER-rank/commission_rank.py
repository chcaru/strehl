"""Commission the ranking statistic before trusting a single ordering it produces.

ORCH's requirement was one arm: "add known noise to a known-sharp frame and
confirm the statistic does not rise." That arm alone is not sufficient, and
this file has now twice proved it.

  NULL      byte-identical copy         -> must move EXACTLY zero
  PLANT     +known Gaussian noise       -> must NOT rise           (ORCH's arm)
  POSITIVE  Gaussian blur               -> MUST fall               (proves alive)
  SPARSITY  detail confined to 1/4 frame-> must NOT rise           (cross-subject)
  RIVAL     the shipped p95 proxy, on the same arms

WHY THE SPARSITY ARM EXISTS -- THE POINT OF THIS FILE
------------------------------------------------------
v2 passed NULL, PLANT, POSITIVE and RIVAL, and was still wrong on the real
corpus: it ranked `coffee-bubbles` first at 1.35 and put `bee-3-cpl`, an
award-quality frame, 12th of 26.

The reason those four arms could not see it: they are ALL same-subject
perturbations. They establish how a statistic responds to a change in ONE
image. A ranking is a claim about DIFFERENT images, so the arms did not test
the thing the statistic is for. Any statistic that is invariant under a
same-image transform can still be wildly incomparable across subjects.

SPARSITY is the missing arm. It dims three quarters of the frame in linear
light, leaving detail confined to a representative quarter -- the geometry of a
dark-background macro shot, and a transformation that unarguably cannot IMPROVE
a photograph. So "must not rise" needs no further justification.

THE ARM HAS TEETH, AND THAT IS CHECKED RATHER THAN ASSUMED
-----------------------------------------------------------
An arm nothing fails tests nothing. So v2 is retained in rank.py purely as the
known-bad reference instrument, and this file REQUIRES v2 to fail SPARSITY. If
v2 passed, the arm would be inert and the run reports NOT COMMISSIONED.

The size of v2's failure is predicted BEFORE it is measured, from the mask
alone, so this confirms the mechanism and not merely the symptom. For a
per-pixel multiplier m applied to an image of otherwise uniform level L and
gradient G:

    detail -> G*sqrt(mean(m^2))        level -> L*mean(m)
    v2 = detail/level  ->  (G/L) * sqrt(mean(m^2))/mean(m)

so v2 must rise by the factor sqrt(mean(m^2))/mean(m), computable from the mask
with no reference to the measurement. Agreement between predicted and measured
is the evidence that v2 fails BECAUSE it rewards sparsity. It also doubles as
the control on the mask itself: the tile boundaries are smoothed precisely so
they do not add gradient of their own, and if they did, the measured rise would
overshoot the prediction badly.

VERDICT CRITERIA, FIXED BEFORE THE RUN
--------------------------------------
  - resolved rises under blur              => FAIL, the statistic is backwards
  - resolved does not fall under blur      => FAIL, it cannot respond
  - resolved rises >1% under planted noise => FAIL, same defect as the proxy
  - resolved rises at all under SPARSITY   => FAIL, v2's defect survives
  - v2 does NOT rise under SPARSITY        => FAIL, the arm is inert and proves
                                              nothing about v3 either

THE 1% NOISE TOLERANCE IS DECLARED IN ADVANCE, WITH ITS REASON. The subtraction
cancels white noise exactly, but noise is planted in the master's encoded uint16
and the statistic linearises before measuring, so what is white going in is
signal-dependent where it is measured; a small residual is expected from the
nonlinearity, not from the statistic being wrong.

HISTORY OF THIS FILE'S OWN FAILURES, kept because each is the argument for an arm:
  v1  P90(|grad|)/sigma   -- blur RAISED it +2358% (sigma is a high-pass and
                             blur destroys it). Caught only by POSITIVE.
  v2  detail/mean(lum)    -- scales as 1/sqrt(f) in the detailed fraction f, so
                             it rewards sparsity. Caught only by SPARSITY.
"""

import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from rank import (  # noqa: E402
    acuity_level,
    linear_to_srgb,
    p95_proxy,
    read_u16,
    resolved_detail,
    srgb_to_linear,
)

NOISE_DN = 300.0   # ~0.46% of full scale; visible, well above any real read noise
BLUR_SIGMA = 1.5   # px; the same potency used to commission crops.py
SPARSE_TILE = 512  # matches the ranking tile, so the arm probes the real geometry
SPARSE_KEEP = 1    # keep 1 tile in 4 bright
SPARSE_OF = 4
SPARSE_DIM = 0.05  # dim, NOT black: a zeroed background would fall outside the
                   # lit-population cut and v2 would escape the defect entirely
SPARSE_SMOOTH = 64.0  # px; blurs tile boundaries so the mask adds no gradient


def sparsity_mask(shape: tuple) -> np.ndarray:
    h, w = shape[0], shape[1]
    ny = int(np.ceil(h / SPARSE_TILE))
    nx = int(np.ceil(w / SPARSE_TILE))
    idx = np.arange(ny * nx).reshape(ny, nx)
    coarse = np.where((idx % SPARSE_OF) < SPARSE_KEEP, 1.0, SPARSE_DIM)
    m = np.kron(coarse, np.ones((SPARSE_TILE, SPARSE_TILE)))[:h, :w]
    return ndi.gaussian_filter(m, SPARSE_SMOOTH)


def apply_mask_linear(img: np.ndarray, m: np.ndarray, encoded: str) -> np.ndarray:
    """Dim in LINEAR light and re-encode, so the arm is a true exposure-like
    operation on that region rather than a curve-domain smear."""
    a = img.astype(np.float64) / 65535.0
    lin = srgb_to_linear(a) if encoded == "srgb" else a
    lin = lin * (m[:, :, None] if lin.ndim == 3 else m)
    out = linear_to_srgb(lin) if encoded == "srgb" else np.clip(lin, 0, 1)
    return np.clip(np.rint(out * 65535.0), 0, 65535).astype(np.uint16)


def arm(name: str, img: np.ndarray, encoded: str) -> tuple:
    r = resolved_detail(img, encoded)["resolved"]
    v2 = acuity_level(img, encoded)
    p = p95_proxy(img)
    print(f"  {name:28s} resolved={r:.6f}   v2={v2:8.4f}   p95={p:.6f}")
    return r, v2, p


def pct(new: float, ref: float) -> str:
    return "n/a" if ref == 0 else f"{(new - ref) / ref * 100.0:+.2f}%"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: commission_rank.py <sharp-master.tiff> [encoded]")
    src = Path(sys.argv[1])
    encoded = sys.argv[2] if len(sys.argv) > 2 else "srgb"

    base = read_u16(src)
    print(f"subject : {src.stem}\nencoded : {encoded}\nshape   : {base.shape}\n")

    print("ARMS")
    r_ref, v_ref, p_ref = arm("reference", base, encoded)

    # NULL: written and re-read rather than the array reused, so an unstable
    # reader or writer would surface here rather than hide.
    tmp = Path(str(src) + ".nullcopy.tiff")
    tifffile.imwrite(str(tmp), base)
    r_null, v_null, p_null = arm("null (byte copy)", read_u16(tmp), encoded)
    tmp.unlink(missing_ok=True)

    rng = np.random.default_rng(20260826)
    noisy = np.clip(base.astype(np.float32)
                    + rng.normal(0.0, NOISE_DN, base.shape), 0, 65535).astype(np.uint16)
    r_noise, v_noise, p_noise = arm(f"PLANT +{NOISE_DN:.0f} DN noise", noisy, encoded)

    sig = (BLUR_SIGMA, BLUR_SIGMA, 0) if base.ndim == 3 else (BLUR_SIGMA, BLUR_SIGMA)
    blurred = ndi.gaussian_filter(base.astype(np.float32), sig).astype(np.uint16)
    r_blur, v_blur, p_blur = arm(f"POSITIVE blur s={BLUR_SIGMA}", blurred, encoded)

    m = sparsity_mask(base.shape)
    predicted = float(np.sqrt(np.mean(m ** 2)) / np.mean(m))
    print(f"\n  sparsity mask: keep {SPARSE_KEEP}/{SPARSE_OF} tiles, dim x{SPARSE_DIM}, "
          f"mean(m)={m.mean():.4f}")
    print(f"  PREDICTED v2 rise from the mask alone: x{predicted:.4f} "
          f"({(predicted - 1) * 100:+.1f}%)  [computed before measuring]\n")
    sparse = apply_mask_linear(base, m, encoded)
    r_sp, v_sp, p_sp = arm("SPARSITY 1/4 frame lit", sparse, encoded)

    print("\nCHANGE vs reference")
    for label, (r, v, p) in [
        ("null    ", (r_null, v_null, p_null)),
        ("+noise  ", (r_noise, v_noise, p_noise)),
        ("blur    ", (r_blur, v_blur, p_blur)),
        ("sparsity", (r_sp, v_sp, p_sp)),
    ]:
        print(f"  {label}  resolved {pct(r, r_ref):>9s}   "
              f"v2 {pct(v, v_ref):>9s}   p95 {pct(p, p_ref):>9s}")

    v2_rise = (v_sp - v_ref) / v_ref * 100.0 if v_ref else 0.0
    print(f"\n  v2 under sparsity: predicted {(predicted - 1) * 100:+.1f}%, "
          f"measured {v2_rise:+.1f}%")

    print("\nVERDICT (criteria fixed before the run)")
    n_rise = (r_noise - r_ref) / r_ref * 100.0 if r_ref else 0.0
    s_rise = (r_sp - r_ref) / r_ref * 100.0 if r_ref else 0.0
    checks = {
        "null moves exactly zero": r_null == r_ref,
        f"planted noise raises resolved <=1% (got {n_rise:+.2f}%)": n_rise <= 1.0,
        "blur DOES lower resolved (statistic is alive)": r_blur < r_ref,
        f"sparsity does NOT raise resolved (got {s_rise:+.2f}%)": s_rise <= 0.0,
        f"ARM HAS TEETH: v2 rises under sparsity (got {v2_rise:+.1f}%)": v2_rise > 10.0,
        "shipped p95 proxy IS fooled by noise (rises)": p_noise > p_ref,
    }
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")

    npass = sum(checks.values())
    print(f"\n{npass}/{len(checks)} passed  ->  "
          f"{'COMMISSIONED' if npass == len(checks) else 'NOT COMMISSIONED'}")
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
