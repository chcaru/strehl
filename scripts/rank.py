"""Rank subjects by how much RESOLVED DETAIL they carry, for display order only.

WHY NOT A GRADIENT PERCENTILE (the shipped proxy)
-------------------------------------------------
`contactsheet.py` orders by the 95th percentile of gradient magnitude. Noise IS
gradient -- uncorrelated pixel-to-pixel differences are the largest gradients in
a dark frame -- so the proxy cannot tell fine texture from read noise. Measured
here: planted noise raises it +0.75%, in the wrong direction.

THE NOISE CORRECTION (kept from v1; it was never the broken part)
------------------------------------------------------------------
    detail = sqrt(max(0, mean(|grad L|^2) - sigma^2))

sigma is Immerkaer's estimator: convolve with

        1 -2  1
       -2  4 -2
        1 -2  1

whose response to any linear ramp is exactly zero, so it sees noise and not
smooth structure; sigma = sqrt(pi/2)/(6N) * sum|conv|.

For white noise of standard deviation sigma, numpy's central-difference
gradient gives each component variance sigma^2/2, so E[|grad|^2] = sigma^2
exactly. Subtracting sigma^2 removes precisely what noise puts in, BY
CONSTRUCTION rather than by tuning. [ARGUED; commissioned by the PLANT arm]

TWO STATISTICS THIS FILE HAS ALREADY GOT WRONG
----------------------------------------------
v1 was P90(|grad|)/sigma. Blur RAISED it +2358%, because Immerkaer's kernel is
a high-pass and blur drives sigma toward zero, so the ratio explodes exactly
when the picture gets worse. It passed the null and passed the planted-noise
arm and was still backwards. Only the blur arm caught it. [MEASURED]

v2 was detail/mean(luminance), frame-wide. It passed all four arms and was
still wrong on the real corpus: it put `coffee-bubbles` first at 1.35 and
pushed `bee-3-cpl` -- an award-quality frame -- to 12th of 26. The mechanism,
derived and then confirmed: if a fraction f of the frame carries detail at
level L and gradient G and the rest is dim, then

    detail ~ sqrt(f)*G      level ~ f*L      ratio ~ G/(L*sqrt(f))

so the statistic scales as 1/sqrt(f) and REWARDS SPARSITY. A mostly-black frame
with a few bright bubbles wins on geometry, not on resolution. [MEASURED]

THE LESSON THAT MATTERS MORE THAN EITHER BUG
--------------------------------------------
v2's four arms -- null, noise, blur, rival -- were ALL same-subject
perturbations. They establish how the statistic responds to changes in ONE
image, and say nothing whatever about whether two DIFFERENT images are
comparable. A ranking is exactly a cross-subject claim, so the arms did not
test the thing the statistic is for. The SPARSITY arm in commission_rank.py
exists to close that gap, and v2 fails it. [ARGUED]

WHAT v3 DOES
------------
Measure detail PER TILE and take a high percentile across tiles:

    resolved = P90 over 512-px tiles of sqrt(max(0, mean|grad L|^2 - sigma^2))

Two changes, each with a reason:

1. PER TILE, NOT FRAME-WIDE. A macro stack is mostly out-of-focus surround by
   construction. A frame-average measures how much background the subject has,
   not how well the tool resolved it. A viewer judges a photograph by its
   best-resolved region, so the statistic looks there. sigma is estimated per
   tile too, because shot noise is signal-dependent and a frame-wide sigma
   over- or under-corrects every tile that is not at the mean level.

2. NO LEVEL NORMALISATION. v2 divided by mean luminance to cancel
   --auto-exposure's per-image gain. That cannot be made to work: a global gain
   and a genuinely dark subject are THE SAME MULTIPLICATION, so no global
   normaliser can distinguish them, and any statistic invariant to the first is
   inflated by the second. Since --auto-exposure has already chosen a
   viewing-appropriate exposure per image, the delivered picture is measured as
   delivered. [ARGUED]

THE TONE CURVE IS STILL UNDONE FIRST. Ship masters are --srgb, and the standing
rule is that nothing numeric is measured across a transfer curve. The curve is
inverted exactly before measuring, so this is a linear-light statistic. That is
not the same as measuring through it, and the noise arithmetic above is only
valid in linear light.

WHAT THIS IS FOR, AND NOT FOR
-----------------------------
Display order only. It is NOT a quality gate, and it does not diagnose WHY a
subject is weak -- a soft merge and an out-of-focus capture both score low, and
telling those apart is BUILD-TRIAGE's job, not this file's. `--verdicts` is the
hook for their answer; this file never invents one.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi
import tifffile

LIT_PCT = 20.0
TILE = 512
TILE_PCT = 90.0
IMMERKAER = np.array([[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]])


def read_u16(p: Path) -> np.ndarray:
    """16-bit TIFF, or refuse. PIL.Image.open silently downconverts 16-bit RGB
    to 8 bits and has corrupted results in this project before."""
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        raise SystemExit(f"{p}: dtype {a.dtype}, expected uint16")
    return a


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1.0 / 2.4) - 0.055)


def to_linear(img: np.ndarray, encoded: str) -> np.ndarray:
    a = img.astype(np.float32) / 65535.0
    if encoded == "srgb":
        return srgb_to_linear(a)
    if encoded != "linear":
        raise SystemExit(f"unknown encoding {encoded!r}")
    return a


def _block_mean(x: np.ndarray, tile: int) -> np.ndarray:
    """Mean over non-overlapping tile x tile blocks; ragged edge is dropped."""
    h = (x.shape[0] // tile) * tile
    w = (x.shape[1] // tile) * tile
    return x[:h, :w].reshape(h // tile, tile, w // tile, tile).mean(axis=(1, 3))


def resolved_detail(img: np.ndarray, encoded: str, tile: int = TILE) -> dict:
    """P90 across tiles of noise-corrected gradient RMS, in linear light."""
    a = to_linear(img, encoded)
    g = a[:, :, 1] if a.ndim == 3 else a
    lum = a.mean(2) if a.ndim == 3 else a

    # Adapt rather than crash on a crop smaller than the nominal tile, so the
    # commissioning arms and the corpus run the identical code path.
    t = min(tile, g.shape[0] // 2, g.shape[1] // 2)
    if t < 16:
        return {"resolved": 0.0, "sigma": 0.0, "grad_rms": 0.0, "level": 0.0,
                "n_tiles": 0, "tile": 0}

    gy, gx = np.gradient(g)
    gsq_t = _block_mean(gy * gy + gx * gx, t)
    # sigma = sqrt(pi/2)/(6N) * sum|conv| = sqrt(pi/2)/6 * mean|conv|
    sig_t = np.sqrt(np.pi / 2.0) / 6.0 * _block_mean(np.abs(
        ndi.convolve(g, IMMERKAER, mode="reflect")), t)
    det_t = np.sqrt(np.maximum(0.0, gsq_t - sig_t * sig_t))

    lit = lum > np.percentile(lum, LIT_PCT)
    return {
        "resolved": float(np.percentile(det_t, TILE_PCT)),
        "sigma": float(np.median(sig_t)),
        "grad_rms": float(np.sqrt(gsq_t.mean())),
        "level": float(np.mean(lum[lit])) if lit.any() else 0.0,
        "n_tiles": int(det_t.size),
        "tile": t,
    }


def acuity_level(img: np.ndarray, encoded: str) -> float:
    """RETRACTED v2 statistic, kept ONLY as the known-bad reference instrument
    the SPARSITY arm must catch. An arm that nothing fails tests nothing.
    Do not use this to rank anything."""
    a = to_linear(img, encoded)
    g = a[:, :, 1] if a.ndim == 3 else a
    lum = a.mean(2) if a.ndim == 3 else a
    lit = lum > np.percentile(lum, LIT_PCT)
    n_lit = int(lit.sum())
    if n_lit < 1000:
        return 0.0
    conv = ndi.convolve(g, IMMERKAER, mode="reflect")
    sigma = float(np.sqrt(np.pi / 2.0) / (6.0 * n_lit) * np.abs(conv[lit]).sum())
    gy, gx = np.gradient(g)
    grad_sq = float(np.mean(gy[lit] ** 2 + gx[lit] ** 2))
    detail = float(np.sqrt(max(0.0, grad_sq - sigma ** 2)))
    level = float(np.mean(lum[lit]))
    return (detail / level) if level > 0 else 0.0


def p95_proxy(img: np.ndarray) -> float:
    """The shipped ordering, reimplemented for comparison ONLY. Deliberately
    computed the same naive way: gradient percentile, no noise correction."""
    a = img.astype(np.float32) / 65535.0
    g = a[:, :, 1] if a.ndim == 3 else a
    gy, gx = np.gradient(g)
    return float(np.percentile(np.hypot(gy, gx), 95))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("src", type=Path, help="directory of 16-bit master TIFFs")
    ap.add_argument("--encoded", default="srgb", choices=["srgb", "linear"],
                    help="transfer curve ON the masters; it is UNDONE before measuring")
    ap.add_argument("--out", type=Path, help="write ranking TSV+JSON here")
    ap.add_argument("--verdicts", type=Path,
                    help="optional TSV <subject>\\t<verdict> from BUILD-TRIAGE; "
                         "carried through verbatim, never invented here")
    ap.add_argument("--also-p95", action="store_true",
                    help="also report the shipped proxy, to show the difference")
    ap.add_argument("--also-v2", action="store_true",
                    help="also report the RETRACTED v2 statistic, for the record")
    ap.add_argument("--tile", type=int, default=TILE)
    args = ap.parse_args()

    verdicts = {}
    if args.verdicts and args.verdicts.exists():
        for line in args.verdicts.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                k, _, v = line.partition("\t")
                verdicts[k.strip()] = v.strip()

    files = sorted(args.src.glob("*.tiff"))
    if not files:
        raise SystemExit(f"no *.tiff under {args.src}")

    rows, failed = [], []
    for p in files:
        subject = p.stem
        try:
            img = read_u16(p)
            m = resolved_detail(img, args.encoded, args.tile)
            if args.also_p95:
                m["p95_shipped"] = p95_proxy(img)
            if args.also_v2:
                m["v2_retracted"] = acuity_level(img, args.encoded)
            m["subject"] = subject
            m["verdict"] = verdicts.get(subject, "")
            rows.append(m)
            print(f"  {subject:38s} resolved={m['resolved']:.5f}  "
                  f"sigma={m['sigma']:.6f}  tiles={m['n_tiles']}")
        except Exception as e:  # noqa: BLE001 - a bad file must not stop the pass
            failed.append((subject, str(e)))
            print(f"  {subject:38s} FAILED: {e}")

    rows.sort(key=lambda r: -r["resolved"])

    # Every input lands in exactly one bucket and the buckets sum to the total,
    # so a file that was skipped cannot be read as one that scored.
    print(f"\nranked {len(rows)}  failed {len(failed)}  total {len(files)}")
    assert len(rows) + len(failed) == len(files)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        cols = ["rank", "subject", "resolved", "sigma", "grad_rms", "level", "n_tiles"]
        if args.also_p95:
            cols.append("p95_shipped")
        if args.also_v2:
            cols.append("v2_retracted")
        cols.append("verdict")
        lines = ["\t".join(cols)]
        for i, r in enumerate(rows, 1):
            vals = [str(i), r["subject"], f"{r['resolved']:.6f}", f"{r['sigma']:.6f}",
                    f"{r['grad_rms']:.6f}", f"{r['level']:.6f}", str(r["n_tiles"])]
            if args.also_p95:
                vals.append(f"{r['p95_shipped']:.6f}")
            if args.also_v2:
                vals.append(f"{r['v2_retracted']:.6f}")
            vals.append(r["verdict"])
            lines.append("\t".join(vals))
        for s, e in failed:
            lines.append(f"-\t{s}\tFAILED\t-\t-\t-\t-\t{e}")
        (args.out / "ranking.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (args.out / "ranking.json").write_text(
            json.dumps({"ranked": rows, "failed": failed, "encoded": args.encoded},
                       indent=2), encoding="utf-8")
        print(f"wrote {args.out / 'ranking.tsv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
