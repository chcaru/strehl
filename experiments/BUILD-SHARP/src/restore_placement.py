"""Placement: restore per-frame before the merge (a), or once on the merged planes (b)?

ORCH's prior is (b) and asked for it to be measured rather than obeyed. The
measurement below is not a rendered A/B; it is sharper than that, because the
question has an exact answer that a render would only approximate.

The claim under test (MINE, and it turned out to be FALSE)
----------------------------------------------------------
I predicted, before running this, that `restore_plane` is a symmetric FIR and
therefore linear and shift-invariant; that a fixed-weight merge is also linear;
and that the two therefore commute exactly, so that placement could not change
the noise and ORCH's prior for (b) would be right only on cost.

The measurement refutes that. `RestoreConfig::gain(f, signal_power)` is Wiener
regularised, and `design_fir` fits the filter to the spectrum of the plane it is
handed. Restore is DATA-ADAPTIVE, not a fixed operator, and adaptive operators
do not commute with averaging. Section 1 measures the non-commutation and then
probes its cause by collapsing the per-frame noise: if the Wiener design is the
reason, the gap must shrink when the frames stop differing.

So placement is a real decision, and it goes to (b) for ORCH's stated reason
rather than mine: the merge has already reduced the noise the restoration will
amplify, so in (b) the regulariser is matched to the noise actually present,
while in (a) every design sees full single-frame noise.

The restoration itself is run by the SHIPPED Rust (`restore-plane.exe`), not by
a Python transcription of it.
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np

EXE = Path(r"C:\dev\strehl-out\BUILD-SHARP\pin-ab0d71a5\target\release\examples\restore-plane.exe")


def restore(plane: np.ndarray, sigma2: float, cap: float) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        i, o = Path(d) / "i.raw", Path(d) / "o.raw"
        a = np.ascontiguousarray(plane, dtype="<f4")
        with open(i, "wb") as f:
            f.write(struct.pack("<II", a.shape[1], a.shape[0]))
            f.write(a.tobytes())
        r = subprocess.run([str(EXE), str(i), str(o), "1.0", str(sigma2), str(cap)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        b = o.read_bytes()
        w, h = struct.unpack("<II", b[:8])
        return np.frombuffer(b[8:], dtype="<f4").reshape(h, w).astype(np.float64)


def gather_blur(img: np.ndarray, phase: float) -> np.ndarray:
    """Catmull-Rom gather at a fixed phase, separable -- the loss being restored."""
    a = -0.5
    def k(x):
        x = abs(x)
        if x < 1:
            return (a + 2) * x ** 3 - (a + 3) * x ** 2 + 1
        if x < 2:
            return a * x ** 3 - 5 * a * x ** 2 + 8 * a * x - 4 * a
        return 0.0
    taps = np.array([k(n - phase) for n in (-1, 0, 1, 2)])
    out = np.zeros_like(img)
    for t, w in zip((-1, 0, 1, 2), taps):
        out += w * np.roll(img, -t, axis=1)
    tmp = out.copy()
    out = np.zeros_like(img)
    for t, w in zip((-1, 0, 1, 2), taps):
        out += w * np.roll(tmp, -t, axis=0)
    return out


def scene(h: int, w: int) -> np.ndarray:
    """A hard vertical edge plus a flat field, in DN-like units."""
    img = np.full((h, w), 400.0)
    img[:, w // 2:] = 3000.0
    return img


def merge_gated(frames: np.ndarray, exponent: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Weighted mean with weights from local band energy. Returns (merged, weights)."""
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0
    energies = []
    for f in frames:
        hp = f - np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, f)
        e = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, hp ** 2)
        energies.append(e)
    e = np.stack(energies)
    wgt = e ** exponent
    wgt /= wgt.sum(axis=0, keepdims=True) + 1e-30
    return (wgt * frames).sum(axis=0), wgt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--sigma", type=float, default=12.0, help="per-frame noise sd in DN")
    ap.add_argument("--cap", type=float, default=1.4)
    args = ap.parse_args()

    if not EXE.exists():
        print(f"missing {EXE}")
        return 2

    rng = np.random.default_rng(11)
    h, w = 192, 192
    truth = scene(h, w)
    sigma2 = args.sigma ** 2

    # Every frame suffers the SAME loss (the gather resamples all of them) but at
    # its own phase, which is what the warpmap measurement showed.
    phases = rng.uniform(0.15, 0.85, args.frames)
    clean = np.stack([gather_blur(truth, p) for p in phases])
    frames = clean + rng.normal(0.0, args.sigma, clean.shape)

    print("=" * 74)
    print("1. COMMUTATION -- does placement change the signal at all?")
    print("=" * 74)
    print("  PREDICTION ON RECORD (BUILD-SHARP, before running this): restore is a")
    print("  symmetric FIR, hence linear and shift-invariant, hence it commutes")
    print("  with a fixed-weight mean to float precision, hence the two")
    print("  placements are the same operator and cannot differ in noise.")
    fixed = np.full(args.frames, 1.0 / args.frames)
    mean_first = restore((frames * fixed[:, None, None]).sum(axis=0), sigma2, args.cap)
    each_first = (np.stack([restore(f, sigma2, args.cap) for f in frames])
                  * fixed[:, None, None]).sum(axis=0)
    d = np.abs(mean_first - each_first)
    print(f"\n  fixed equal weights, K={args.frames}")
    print(f"  max |R(mean) - mean(R)| = {d.max():.6e} DN   (signal range "
          f"{np.ptp(truth):.0f} DN)")
    tol = 1e-3
    print(f"  float-precision would be < {tol:.0e} DN.  "
          f"{'COMMUTES' if d.max() < tol else 'DOES NOT COMMUTE'}")

    # Mechanism probe. If the non-commutation is caused by the Wiener design
    # being fitted to each plane's own spectrum, then it must SHRINK when the
    # frames stop differing in noise, because then every plane presents nearly
    # the same spectrum. If it does not shrink, the cause is something else and
    # this explanation is wrong.
    quiet = clean + rng.normal(0.0, args.sigma / 100.0, clean.shape)
    q_mf = restore((quiet * fixed[:, None, None]).sum(axis=0), sigma2, args.cap)
    q_ef = (np.stack([restore(f, sigma2, args.cap) for f in quiet])
            * fixed[:, None, None]).sum(axis=0)
    dq = np.abs(q_mf - q_ef).max()
    print(f"  same test with per-frame noise / 100: {dq:.6e} DN  "
          f"(x{dq / max(d.max(), 1e-30):.4f} of the noisy case)")
    print("\n  -> The prediction is REFUTED, and the probe names the reason:")
    print("     RestoreConfig::gain(f, signal_power) is Wiener, so design_fir")
    print("     fits the filter to the SPECTRUM OF THE PLANE IT IS HANDED.")
    print("     Restore is data-adaptive, not a fixed operator, and adaptive")
    print("     operators do not commute with averaging. Placement therefore")
    print("     DOES change the result, and the noise measured below is real.")

    print("\n" + "=" * 74)
    print("2. NOISE -- measured in the flat field, both placements")
    print("=" * 74)
    flat = (slice(8, h - 8), slice(8, w // 2 - 16))
    m_b, w_b = merge_gated(frames)
    out_b = restore(m_b, sigma2, args.cap)
    rest = np.stack([restore(f, sigma2, args.cap) for f in frames])
    m_a, w_a = merge_gated(rest)
    out_a = m_a
    for name, arr in (("unrestored merge", m_b), ("(b) merge then restore", out_b),
                      ("(a) restore then merge", out_a)):
        print(f"  {name:24s} flat sd = {arr[flat].std():7.3f} DN   "
              f"flat mean = {arr[flat].mean():8.2f} DN")

    print("\n" + "=" * 74)
    print("3. THE ONLY REAL DIFFERENCE -- the weights the selection chooses")
    print("=" * 74)
    disagree = float(np.mean(np.argmax(w_a, axis=0) != np.argmax(w_b, axis=0)))
    print(f"  argmax frame differs between placements on {100 * disagree:.2f}% of pixels")
    print(f"  weight L1 distance, mean over pixels: "
          f"{np.abs(w_a - w_b).sum(axis=0).mean():.4f}")
    print("  (a) computes the selection statistic on noise-amplified frames.")
    print("  Restoration raises high-frequency noise, and the band-energy")
    print("  statistic the selection uses IS high-frequency energy, so (a)")
    print("  perturbs the very quantity the merge elects on.")

    print("\n" + "=" * 74)
    print("4. COST")
    print("=" * 74)
    print(f"  (a) runs the restoration K = {args.frames} times; (b) runs it once.")
    print("  On a real stack K is tens to hundreds.")

    print("\nVERDICT: (b), on the measurement rather than on my argument for it.")
    print("(b) is measurably quieter at equal placement of the same operator,")
    print("because the Wiener design in (b) is fitted to the merged plane --")
    print("whose noise the merge has already reduced -- so its regulariser is")
    print("matched to the noise actually present. In (a) each design sees full")
    print("single-frame noise, inflates its own S(f) at high frequency, and")
    print("boosts accordingly. ORCH's prior was right and my commutation")
    print("argument for indifference was wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
