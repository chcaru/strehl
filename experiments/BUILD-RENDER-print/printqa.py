"""Print QA for the shipped masters: gamut, ICC correctness, and headroom.

MEASUREMENT STANCE
------------------
The masters are `--srgb` renders, so their pixels sit behind a transfer curve
and the standing rule is never to measure through one.  Colour is the one
question where decoding the curve IS the measurement: a gamut answer is a
colorimetric answer, and colorimetry is defined on linear light.  So every
number here is computed after an exact sRGB decode to linear, through XYZ and
Bradford adaptation to the D50 connection space the print profile uses.  No
statistic is taken on the encoded values.  The one exception is the CMYK
round-trip itself, which LittleCMS performs through the profile's own curves.

WHAT IS MEASURED
----------------
1. Out-of-gamut coverage against a real `prtr`-class CMYK profile, as the
   fraction of pixels a print cannot reproduce, split into a chroma component
   (too saturated to print) and the remainder (too dark or too light).
2. Whether the embedded ICC profile agrees with the encoded data, by a null:
   converting a master through its own embedded profile to sRGB must not move
   pixels, because the embedded profile IS sRGB.
3. Shadow and highlight headroom in L*, which is what a print crushes, plus a
   hard count of channel clipping, which is unambiguous.

WHY THE CONTROLS ARE HERE
-------------------------
A gamut instrument that reports low coverage on everything is indistinguishable
from a print process that can reproduce everything, and this project has
shipped that mistake before.  So the instrument is commissioned against colours
whose answer is fixed by construction: saturated sRGB primaries must read
almost entirely out of gamut, and a neutral grey ramp must read almost entirely
in gamut.  If either fails, no subject result is reported.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageCms

SRGB_TO_XYZ_D65 = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)
BRADFORD_D65_TO_D50 = np.array(
    [
        [1.0478112, 0.0228866, -0.0501270],
        [0.0295424, 0.9904844, -0.0170491],
        [-0.0092345, 0.0150436, 0.7521316],
    ],
    dtype=np.float64,
)
WHITE_D50 = np.array([0.96422, 1.00000, 0.82521], dtype=np.float64)

SRGB_ICM = Path(r"C:\Windows\System32\spool\drivers\color\sRGB Color Space Profile.icm")
SWOP_ICM = Path(r"C:\Windows\System32\spool\drivers\color\RSWOP.icm")

DE_GAMUT = 2.0  # dE76, reported only
CHROMA_LOSS_LIMIT = 2.0  # Lab chroma units the press cannot reach

SATURATED_CHROMA = 20.0
"""Master chroma (C* = hypot(a,b)) above which a pixel counts as carrying real
colour rather than a tint.

Not arbitrary: `flower-inner-edge-cpl`, the most saturated master in the
corpus, has a MEASURED mean chroma of 20.14, so this threshold sits at the
mean of the corpus's most colourful frame -- above it is the saturated half of
the most saturated subject. Its purpose is to separate "the press flattened a
colour" from "the press nudged a near-neutral", which the unconditioned
statistic cannot do."""


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    """Exact sRGB decode.  x in [0,1]."""
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def rgb_to_lab(rgb01: np.ndarray) -> np.ndarray:
    """sRGB-encoded [0,1] -> CIE L*a*b* on the D50 connection space."""
    lin = srgb_to_linear(rgb01.astype(np.float64))
    m = (BRADFORD_D65_TO_D50 @ SRGB_TO_XYZ_D65).T
    xyz = lin.reshape(-1, 3) @ m
    r = xyz / WHITE_D50
    eps = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    f = np.where(r > eps, np.cbrt(r), (kappa * r + 16.0) / 116.0)
    lab = np.empty_like(f)
    lab[:, 0] = 116.0 * f[:, 1] - 16.0
    lab[:, 1] = 500.0 * (f[:, 0] - f[:, 1])
    lab[:, 2] = 200.0 * (f[:, 1] - f[:, 2])
    return lab.reshape(rgb01.shape)


def embedded_profile(path: Path) -> bytes | None:
    with tifffile.TiffFile(path) as tf:
        tag = tf.pages[0].tags.get("InterColorProfile")
        if tag is None:
            return None
        v = tag.value
        return v if isinstance(v, bytes) else bytes(v)


def read_master(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    if a.dtype != np.uint16:
        raise SystemExit(f"REFUSED: {path.name} is {a.dtype}, not uint16")
    if a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit(f"REFUSED: {path.name} has shape {a.shape}, not H x W x 3")
    return a


def profile_mode(profile) -> str:
    """The PIL image mode matching a profile's own colour space.

    Not assumed. The first version hardcoded CMYK, which is right for a press
    profile like RSWOP and wrong for a great many fine-art inkjet profiles,
    which are RGB because the printer driver presents an RGB interface. Passing
    an RGB output profile to a CMYK-typed transform does not mis-measure, it
    raises `cannot build transform` -- so the failure is loud, but it would
    have arrived at exactly the moment the owner's real profile did.
    """
    space = str(getattr(profile.profile, "xcolor_space", "")).strip().upper()
    if space == "CMYK":
        return "CMYK"
    if space in ("RGB", "GRAY"):
        return "RGB" if space == "RGB" else "L"
    raise SystemExit(
        f"REFUSED: profile colour space {space!r} is not one this tool can "
        "round-trip; add it deliberately rather than guessing a mode."
    )


def printable_rgb8(rgb8: np.ndarray, dest, srgb) -> np.ndarray:
    """Send 8-bit sRGB through the print profile and back: what the press can do.

    Black point compensation is ON.  Without it the press's black, which is far
    lighter than sRGB's, drags every shadow tone and the round-trip difference
    is dominated by dynamic range rather than by gamut.  That is a real print
    concern, but it is a DIFFERENT one, and it is reported separately as tonal
    compression rather than folded into a gamut number.
    """
    flags = ImageCms.Flags.BLACKPOINTCOMPENSATION | ImageCms.Flags.HIGHRESPRECALC
    mode = profile_mode(dest)
    im = Image.fromarray(rgb8, "RGB")
    fwd = ImageCms.buildTransform(
        srgb, dest, "RGB", mode, renderingIntent=1, flags=flags
    )
    back = ImageCms.buildTransform(
        dest, srgb, mode, "RGB", renderingIntent=1, flags=flags
    )
    return np.asarray(ImageCms.applyTransform(ImageCms.applyTransform(im, fwd), back))


def gamut_stats(rgb16: np.ndarray, swop, srgb, shift: bool = True, sat_grid: tuple = ()) -> dict:
    """Out-of-gamut judged on CHROMA THE PRESS CANNOT REACH.

    The first version of this scored total dE and a neutral grey ramp came back
    96.5% out of gamut, which is a statement about the instrument and not about
    any press.  Chroma loss is the question actually being asked -- can the ink
    get this saturated -- and a neutral has no chroma to lose, so the control
    can no longer be tripped by tone mapping.
    """
    rgb8 = (
        (rgb16 >> 8).astype(np.uint8)
        if shift
        else np.rint(rgb16.astype(np.float64) / 257.0).astype(np.uint8)
    )
    lab_orig = rgb_to_lab(rgb16 / 65535.0)
    lab_print = rgb_to_lab(printable_rgb8(rgb8, swop, srgb) / 255.0)

    d = lab_orig - lab_print
    de = np.sqrt((d * d).sum(axis=-1))
    c_orig = np.hypot(lab_orig[..., 1], lab_orig[..., 2])
    c_print = np.hypot(lab_print[..., 1], lab_print[..., 2])
    lost_chroma = c_orig - c_print

    oog = lost_chroma > CHROMA_LOSS_LIMIT

    # A loss of 5 Lab units is not one fact. Taken off a saturated flower it
    # flattens the subject; taken off a near-neutral background it is a grey
    # going very slightly warm and no viewer will find it. `severe_pct` alone
    # cannot tell those apart -- LOOKING at flowers-cpl is what exposed this:
    # its densest out-of-gamut window is featureless background bokeh where
    # MASTER and PRINTABLE are indistinguishable by eye, yet the window scored
    # 90.5%. So condition the loss on there being saturation to lose.
    saturated = c_orig >= SATURATED_CHROMA
    n_sat = int(saturated.sum())
    n = de.size

    # `SATURATED_CHROMA` is a number I chose, and a threshold read off one
    # working value flatters the instrument: the verdicts it gates cannot be
    # audited without the grid behind them. Scoring the whole grid here reuses
    # the single ICC round trip above, which is the expensive part, so the
    # audit costs one pass rather than one per threshold.
    grid = {}
    for thr in sat_grid:
        sat_t = c_orig >= thr
        n_t = int(sat_t.sum())
        grid[thr] = {
            "sat_pct": 100.0 * n_t / n,
            "sat_severe_pct": 100.0 * (sat_t & (lost_chroma > 5.0)).sum() / n,
            "sat_rel_loss_p90": (
                float(np.percentile(lost_chroma[sat_t] / c_orig[sat_t], 90))
                if n_t > 0
                else float("nan")
            ),
        }

    return {
        "oog_pct": 100.0 * oog.sum() / n,
        "severe_pct": 100.0 * (lost_chroma > 5.0).sum() / n,
        # How much genuinely saturated colour the frame contains at all. Without
        # this, sat_severe_pct = 0 is ambiguous between "the press held it" and
        # "there was never any saturated colour here".
        "sat_pct": 100.0 * n_sat / n,
        "sat_severe_pct": 100.0 * (saturated & (lost_chroma > 5.0)).sum() / n,
        "sat_rel_loss_p90": (
            float(np.percentile(lost_chroma[saturated] / c_orig[saturated], 90))
            if n_sat > 0
            else float("nan")
        ),
        "de_p99": float(np.percentile(de, 99)),
        "chroma_loss_p99": float(np.percentile(lost_chroma, 99)),
        "chroma_loss_max": float(lost_chroma.max()),
        "tonal_dL_p99": float(np.percentile(np.abs(d[..., 0]), 99)),
        "mean_chroma": float(c_orig.mean()),
        "sat_grid": grid,
        "lab": lab_orig,
    }


def headroom_stats(rgb16: np.ndarray, lab: np.ndarray) -> dict:
    lightness = lab[..., 0]
    n = lightness.size
    return {
        "shadow_pct": 100.0 * (lightness < 5.0).sum() / n,
        "highlight_pct": 100.0 * (lightness > 95.0).sum() / n,
        "L_p01": float(np.percentile(lightness, 1)),
        "L_p99": float(np.percentile(lightness, 99)),
        "clip_black_pct": 100.0 * (rgb16 == 0).all(axis=-1).sum() / n,
        "clip_white_pct": 100.0 * (rgb16 == 65535).any(axis=-1).sum() / n,
    }


def icc_null(path: Path, rgb16: np.ndarray, srgb) -> dict:
    """The embedded profile must BE sRGB, so converting through it must be a no-op."""
    prof = embedded_profile(path)
    if prof is None:
        return {"profile": "ABSENT", "class": None, "max_delta": None}
    p = ImageCms.getOpenProfile(io.BytesIO(prof))
    rgb8 = (rgb16 >> 8).astype(np.uint8)
    tr = ImageCms.buildTransform(p, srgb, "RGB", "RGB", renderingIntent=1)
    out = np.asarray(ImageCms.applyTransform(Image.fromarray(rgb8, "RGB"), tr))
    return {
        "profile": p.profile.profile_description,
        "class": p.profile.device_class,
        "max_delta": int(np.abs(out.astype(np.int16) - rgb8.astype(np.int16)).max()),
    }


def commission(swop, srgb) -> bool:
    """Colours whose answer is fixed by construction, not measured."""
    ok = True
    print("COMMISSIONING (no subject result is reported unless all of these pass)")

    sat = np.zeros((64, 192, 3), np.uint16)
    for i in range(3):
        sat[:, i * 64 : (i + 1) * 64, i] = 65535
    hit = gamut_stats(sat, swop, srgb)["oog_pct"]
    print(f"  POSITIVE  saturated sRGB primaries   out-of-gamut {hit:6.2f}%  need > 90")
    if hit <= 90.0:
        print("    FAIL -- cannot see colour a press demonstrably cannot print")
        ok = False

    ramp = np.linspace(0, 65535, 256).astype(np.uint16)
    ramp = np.repeat(np.repeat(ramp[None, :, None], 64, axis=0), 3, axis=2)
    g = gamut_stats(ramp, swop, srgb)["oog_pct"]
    print(f"  NULL      neutral grey ramp          out-of-gamut {g:6.2f}%  need < 2")
    if g >= 2.0:
        print("    FAIL -- flags neutrals, which have no chroma to lose")
        ok = False

    # An instrument that says "yes" to anything coloured passes both of the
    # above.  This one has to grade: same hue, rising saturation, rising answer.
    grey = np.array([128, 128, 128], np.float64)
    pure = np.array([0, 255, 0], np.float64)
    ladder = []
    for f in (0.0, 0.25, 0.5, 0.75, 1.0):
        patch = np.rint((1 - f) * grey + f * pure).astype(np.uint16) * 257
        patch = np.tile(patch, (64, 64, 1)).astype(np.uint16)
        ladder.append(gamut_stats(patch, swop, srgb)["oog_pct"])
    rungs = "  ".join(f"{v:5.1f}" for v in ladder)
    mono = all(b >= a - 0.01 for a, b in zip(ladder, ladder[1:]))
    span = ladder[-1] - ladder[0]
    print(f"  RESPONSE  grey->green chroma ladder  {rungs}")
    print(f"            monotone {mono}, span {span:.1f} points   need both, span > 50")
    if not mono or span <= 50.0:
        print("    FAIL -- does not grade saturation; it is a yes/no on colour")
        ok = False

    a = gamut_stats(sat, swop, srgb, shift=True)["oog_pct"]
    b = gamut_stats(sat, swop, srgb, shift=False)["oog_pct"]
    print(f"  PRECISION 8-bit quantisation bound   {abs(a - b):6.3f} points  need < 0.50")
    if abs(a - b) >= 0.5:
        print("    FAIL -- the answer is driven by quantisation, not by gamut")
        ok = False

    print("  COMMISSIONED" if ok else "  REFUSED -- no subject numbers follow")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(r"C:\dev\strehl-out\SHIP-V2-ICC"))
    ap.add_argument("--profile", type=Path, default=SWOP_ICM)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    for p in (SRGB_ICM, args.profile):
        if not p.exists():
            print(f"REFUSED: profile not found: {p}")
            return 1

    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    swop = ImageCms.getOpenProfile(str(args.profile))
    info = swop.profile
    print(f"print target : {info.profile_description}")
    print(f"               {info.xcolor_space.strip()} / {info.device_class} / v{info.version}")
    print(f"               {args.profile}")
    print("               NOT an inkjet profile: SWOP is web-coated offset, and a")
    print("               fine-art inkjet gamut differs, wider in saturated greens")
    print("               and blues.  Treat this as a print-class proxy until the")
    print("               owner's lab profile is in hand.")
    print()
    if not commission(swop, srgb):
        return 1
    print()

    masters = sorted(args.root.glob("*.tiff"))
    if args.limit:
        masters = masters[: args.limit]
    if not masters:
        print(f"NO MASTERS under {args.root} -- nothing examined, which is not a pass")
        return 1

    hdr = (
        f"{'subject':<36}{'OOG%':>7}{'sev%':>7}{'Cmax':>7}{'dL p99':>8}"
        f"{'shadow%':>9}{'high%':>7}{'clipW%':>8}{'null':>7}"
    )
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for m in masters:
        rgb16 = read_master(m)
        g = gamut_stats(rgb16, swop, srgb)
        h = headroom_stats(rgb16, g["lab"])
        i = icc_null(m, rgb16, srgb)
        name = m.name.replace("--SHIP-V2-ICC.tiff", "").replace(".tiff", "")
        rows.append((name, g, h, i))
        nul = "ABSENT" if i["max_delta"] is None else str(i["max_delta"])
        print(
            f"{name:<36}{g['oog_pct']:7.2f}{g['severe_pct']:7.2f}"
            f"{g['chroma_loss_max']:7.1f}{g['tonal_dL_p99']:8.2f}"
            f"{h['shadow_pct']:9.2f}{h['highlight_pct']:7.2f}"
            f"{h['clip_white_pct']:8.3f}{nul:>7}"
        )

    print()
    print(f"subjects examined : {len(rows)}")
    absent = sum(1 for _, _, _, i in rows if i["max_delta"] is None)
    exact = sum(1 for _, _, _, i in rows if i["max_delta"] == 0)
    quant = sum(1 for _, _, _, i in rows if i["max_delta"] == 1)
    moved = sum(
        1 for _, _, _, i in rows if i["max_delta"] is not None and i["max_delta"] > 1
    )
    print(f"  ICC null exact (0 DN)      : {exact}")
    print(f"  ICC null 1 DN (8-bit round): {quant}")
    print(f"  ICC null moved (>1 DN)     : {moved}   <- would indicate a wrong profile")
    print(f"  ICC profile absent         : {absent}")
    print(
        f"  TOTAL                      : {exact + quant + moved + absent}"
        f"  (must equal {len(rows)})"
    )
    descs = {i["profile"] for _, _, _, i in rows}
    print(f"  distinct profiles     : {len(descs)} -> {sorted(descs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
