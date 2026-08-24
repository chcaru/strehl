"""M109 step 0: reproduce the magenta arithmetic on paper, before touching code.

Nothing here decodes a RAW file. It takes the numbers SYNTHESIS fact 1432
already measured -- the raw per-channel means inside the magenta blob of
`DSC00150.ARW`, the as-shot WB multipliers, and the A7C II characterisation
matrix that `image_out.rs`'s tests already carry -- and pushes them through the
render path exactly as `merge_cmd::write_merged` -> `image_out::develop_pixel`
implements it:

    lin_c = (raw_c - black) * gain_c * exposure_gain / (white - black)
    v     = camera_to_srgb(xyz_to_cam) * lin
    v     = clamp(v, 0, 1)
    out   = srgb_encode(v)

Its job is to answer three questions BEFORE any expensive render:

  Q1  does the arithmetic reproduce fact 1432's output triple
      (R=0.9944 G=0.8915 B=0.9943)?  If it does not, the mechanism is not what
      was measured and the milestone stops.
  Q2  is the defect exposure-dependent?  `argmax-baseline` has no exposure knob
      at all (StackOptions has no exposure field), so if the magenta predicate
      only fires at eg < 1 then argmax-baseline cannot be used as the
      demonstration path and the fix must reach `merge_cmd.rs`.
  Q3  does the proposed fix -- one common ceiling applied to all three channels
      in white-balanced camera space, BEFORE the matrix -- turn the blob
      neutral, and does it leave a genuinely saturated colour alone?

Run: python experiments/M109-highlights/src/mechanism.py
"""

import numpy as np

# ---------------------------------------------------------------------------
# Inputs, every one of them cited.
# ---------------------------------------------------------------------------

# SYNTHESIS fact 1432: raw sensel means inside the magenta blob of DSC00150.ARW.
BLOB = dict(R=7673.2, G1=16383.0, B=14116.0, G2=16383.0)
# SYNTHESIS fact 1432: a neutral white reference region on the same frame.
WHITE_REF = dict(R=2569.0, G=5865.0, B=3937.0)
# AGENTS.md "Reference rig": black 512, white 15360, confirmed by measurement.
BLACK, WHITE = 512.0, 15360.0
# clip.rs CONTAINER_MAX_DN -- the 14-bit container maximum. NOT Levels::white.
CONTAINER_MAX = 16383.0
# fact 1432: camera WB multipliers [2751, 1024, 1569, 1024] -> green-normalised.
GAINS = np.array([2751.0 / 1024.0, 1.0, 1569.0 / 1024.0])
# image_out.rs tests, const A7C2: xyz_to_cam for the ILCE-7CM2 (M26 §1, M85).
A7C2 = np.array([
    [0.7460, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
])
# color.rs SRGB_TO_XYZ_D65.
SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
# The exposure --auto-exposure chose on `marker` at HEAD 8f46f04 (fact 1432).
STOPS = -0.24


def camera_to_srgb(xyz_to_cam):
    """color::camera_to_srgb, transcribed: compose, row-normalise, invert."""
    cam_from_srgb = xyz_to_cam @ SRGB_TO_XYZ
    cam_from_srgb = cam_from_srgb / cam_from_srgb.sum(axis=1, keepdims=True)
    return np.linalg.inv(cam_from_srgb)


def srgb_encode(v):
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)


M = camera_to_srgb(A7C2)
RANGE = WHITE - BLACK
# The one number the whole fix turns on: where a container-pinned sample lands
# in the render's normalised, white-balanced camera space, before exposure.
# Green's WB gain is 1.0 by construction (green-normalised), so this is also
# green's ceiling, and green is the channel that saturates first.
K0 = (CONTAINER_MAX - BLACK) / RANGE


def norm(raw, gain, eg):
    return max(raw - BLACK, 0.0) * gain * eg / RANGE


def render(raw_rgb, eg, ceiling=None):
    """The shipped render path, with the proposed clip optional."""
    lin = np.array([norm(raw_rgb[i], GAINS[i], eg) for i in range(3)])
    if ceiling is not None:
        lin = np.minimum(lin, ceiling * eg)
    v = np.clip(M @ lin, 0.0, 1.0)
    return lin, srgb_encode(v)


def magenta(out):
    R, G, B = out
    return (R - G > 0.06) and (B - G > 0.06)


def report(name, raw_rgb, eg, ceiling=None):
    lin, out = render(raw_rgb, eg, ceiling)
    tag = "FIXED " if ceiling is not None else "SHIPPED"
    print(f"  {tag} {name:<22s} eg={eg:.4f}  "
          f"cam_lin=({lin[0]:.4f},{lin[1]:.4f},{lin[2]:.4f})  "
          f"out=({out[0]:.4f},{out[1]:.4f},{out[2]:.4f})  "
          f"R-G={out[0]-out[1]:+.4f}  B-G={out[2]-out[1]:+.4f}  "
          f"magenta={'YES' if magenta(out) else 'no'}")
    return out


def main():
    np.set_printoptions(precision=4, suppress=True)
    print("camera_to_srgb rows (each must sum to 1 -- neutral in, neutral out):")
    for r in M:
        print(f"    [{r[0]:+.4f} {r[1]:+.4f} {r[2]:+.4f}]  sum {r.sum():.6f}")
    print(f"\nWB gains (green-normalised): R {GAINS[0]:.4f} G {GAINS[1]:.4f} "
          f"B {GAINS[2]:.4f}")
    print(f"levels: black {BLACK:.0f} white {WHITE:.0f} range {RANGE:.0f}; "
          f"container max {CONTAINER_MAX:.0f}")
    print(f"K0 = (container - black)/(white - black) = {K0:.6f}")

    blob = np.array([BLOB["R"], 0.5 * (BLOB["G1"] + BLOB["G2"]), BLOB["B"]])
    ref = np.array([WHITE_REF["R"], WHITE_REF["G"], WHITE_REF["B"]])
    eg = 2.0 ** STOPS

    print("\nQ1/Q2 -- the blob, as shipped:")
    got = report("blob", blob, eg)
    want = np.array([0.9944, 0.8915, 0.9943])
    print(f"       fact 1432 reports mean out = ({want[0]:.4f},{want[1]:.4f},"
          f"{want[2]:.4f}); this single-point arithmetic gives "
          f"({got[0]:.4f},{got[1]:.4f},{got[2]:.4f})")
    report("blob", blob, 1.0)
    print("       ^ eg = 1.0 is what `argmax-baseline --srgb` renders at: "
          "StackOptions has no exposure field.")

    print("\nQ3 -- the fix, one common ceiling K0 in camera space before the matrix:")
    report("blob", blob, eg, ceiling=K0)
    report("blob", blob, 1.0, ceiling=K0)

    print("\n  controls -- things the fix must NOT move:")
    for nm, rgb in [
        ("neutral white ref", ref),
        ("saturated red (R pinned)", np.array([CONTAINER_MAX, 3000.0, 2000.0])),
        ("mid grey", np.array([4000.0, 8000.0, 6000.0])),
    ]:
        a = render(rgb, eg)[1]
        b = render(rgb, eg, ceiling=K0)[1]
        d = np.abs(a - b).max()
        print(f"    {nm:<26s} shipped=({a[0]:.4f},{a[1]:.4f},{a[2]:.4f})  "
              f"fixed=({b[0]:.4f},{b[1]:.4f},{b[2]:.4f})  max|delta|={d:.6f}")

    print("\n  the null, stated as arithmetic rather than as a hope:")
    print(f"    the clip is min(x, {K0:.6f} * eg).  A stack whose raw maximum is")
    print(f"    m DN has max lin = (m - {BLACK:.0f}) * gain * eg / {RANGE:.0f}, so the clip is")
    print(f"    the identity whenever (m - black) * gain <= container - black,")
    print(f"    i.e. m <= {BLACK + (CONTAINER_MAX - BLACK):.0f} for green (gain 1) and")
    print(f"    m <= {BLACK + (CONTAINER_MAX - BLACK) / GAINS[0]:.0f} for red (gain {GAINS[0]:.4f}).")


if __name__ == "__main__":
    main()
