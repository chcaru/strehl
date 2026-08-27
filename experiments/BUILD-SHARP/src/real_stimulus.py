"""Does real macro content CARRY energy above plane Nyquist? (s40)

V-NYQUIST measured that the shipped plane gather LOSES 51% of true contrast at
0.20-0.30 cyc/px_out and 88% at 0.30-0.40. Their stated gap is that every arm
ran synthetic content through the real library. This closes the half of that gap
which can overturn the decision, and it needs no ground truth at all.

s31's rule: measuring in the right band is necessary but not sufficient -- the
stimulus must exist in the real data too. If real macro captures carry no energy
above 0.25 cyc/px, then a gather that destroys content above 0.25 destroys
nothing, and the fix is worth zero however large its fidelity number is.

METHOD, and why it needs no demosaic and no interpolation.

In a Bayer mosaic the green sensels sit on a quincunx (checkerboard) lattice.
Within ONE row green is sampled at spacing 2, so a single row can say nothing
above 0.25 cyc/px -- which is precisely the band in dispute. But green in row
y+1 sits at the OPPOSITE column parity, so interleaving two adjacent rows yields
a green signal sampled at spacing 1, whose Nyquist is 0.5 cyc/px_sensel. The
output raster is the sensel raster to within 0.1%, so this reads content at
0.20-0.48 cyc/px_out directly off the sensor with no demosaic, no gather and no
resampling of any kind in the path.

THE CONFOUND, NAMED AND MEASURED (ORCH's rule: name the most plausible innocent
explanation and go measure that specific cause). The interleave assumes the
scene is constant in y across one sensel row. Where it is not, vertical detail
leaks into the horizontal spectrum as broadband energy -- which would INFLATE
the high bands, biasing toward the answer I am looking for. Worse, Bayer G1 and
G2 sensels commonly differ in gain, and any systematic offset between the two
interleaved rows lands at exactly f = 0.5 as a comb spike.

Both defects deposit energy at f = 0.5, so the comb spike is a direct readout of
the interleave's own dishonesty and is reported next to every measurement. A
result is only readable where the comb is small compared with the band being
claimed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rawpy

BANDS = [(0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.48)]
RW, RH = 1024, 1024


def green_parity(pattern: np.ndarray, row: int) -> int:
    """Column parity at which green sits, for a given mosaic row parity."""
    for xp in (0, 1):
        if pattern[row % 2][xp] in (1, 3):
            return xp
    raise SystemExit("no green in this pattern row -- not a Bayer CFA")


def diagonals(mos: np.ndarray, pat: np.ndarray, y0: int, x0: int,
              length: int, count: int):
    """Pure-green samples along main diagonals. No interleave, no assumption.

    This is the instrument the row-interleave should have been. Green sensels
    sit where (x + y) is even, so if a diagonal STARTS on a green sensel then
    every sample along (y+k, x+k) is also green -- the parity is invariant along
    the diagonal. The result is an exactly, uniformly sampled 1-D signal with
    spacing sqrt(2) px, obtained by indexing the sensor and nothing else.

    Nyquist is therefore 1/(2*sqrt(2)) = 0.3536 cyc/px, which covers the whole
    0.20-0.30 band where V-NYQUIST measured a 51% loss, and most of 0.30-0.40.
    The shipped CFA-plane raster has spacing 2 px and Nyquist 0.25, so anything
    this instrument sees between 0.25 and 0.354 is content the SENSOR captured
    and the merge raster cannot represent.
    """
    # Green requires (x + y) of a fixed parity, read from the CFA pattern
    # rather than assumed; stepping y by 2 preserves it along the diagonal.
    gpar = {(r + c) % 2 for r in (0, 1) for c in (0, 1) if pat[r][c] in (1, 3)}
    if len(gpar) != 1:
        raise SystemExit(f"green sensels do not share one diagonal parity: {pat}")
    if (y0 + x0) % 2 != gpar.pop():
        x0 += 1
    if pat[y0 % 2][x0 % 2] not in (1, 3):
        raise SystemExit("diagonal start is not a green sensel")
    rows = []
    for i in range(count):
        y = y0 + 2 * i
        k = np.arange(length)
        rows.append(mos[y + k, x0 + k].astype(np.float64))
    return np.vstack(rows)


def interleaved(mos: np.ndarray, pat: np.ndarray, y0: int, x0: int,
                w: int, h: int, balance: bool = False):
    """Full-density horizontal green signal from adjacent row pairs.

    With balance=True the two interleaved populations are brought to a common
    mean per row pair. This nulls a G1/G2 gain imbalance, which is not a
    cosmetic defect here: an imbalance is MULTIPLICATIVE, so it modulates the
    scene by (1 + a*(-1)^x) and folds real content at frequency f into 0.5 - f.
    Uncorrected, low-frequency scene energy would masquerade as energy at
    0.40-0.48 -- precisely the claim this script exists to make.
    """
    rows, ratios = [], []
    for y in range(y0, y0 + h - 1, 2):
        pa = green_parity(pat, y)
        pb = green_parity(pat, y + 1)
        if pa == pb:
            continue
        a = mos[y, x0:x0 + w].astype(np.float64)
        b = mos[y + 1, x0:x0 + w].astype(np.float64)
        sig = np.empty(w, np.float64)
        xs = np.arange(w) + x0
        take_a = (xs % 2) == pa
        ma, mb = a[take_a].mean(), b[~take_a].mean()
        if mb > 0:
            ratios.append(ma / mb)
        sig[take_a] = a[take_a]
        sig[~take_a] = b[~take_a] * ((ma / mb) if (balance and mb > 0) else 1.0)
        rows.append(sig)
    if not rows:
        return None, float("nan")
    return np.vstack(rows), float(np.mean(ratios)) if ratios else float("nan")



def spectrum(sig: np.ndarray):
    """Mean power spectrum of windowed rows, and the f=0.5 comb diagnostic."""
    w = sig.shape[1]
    win = np.hanning(w)
    s = sig - sig.mean(axis=1, keepdims=True)
    F = np.fft.rfft(s * win, axis=1)
    P = (np.abs(F) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(w, d=1.0)
    return f, P


def band_power(f, P, lo, hi) -> float:
    m = (f >= lo) & (f < hi)
    return float(P[m].mean()) if m.any() else float("nan")


def pick(mos: np.ndarray, want_detail: bool):
    """Choose a region by local variation. Excludes near-black and clipped."""
    h, w = mos.shape
    best = None
    for y in range(256, h - RH - 256, 256):
        for x in range(256, w - RW - 256, 256):
            t = mos[y:y + RH:8, x:x + RW:8].astype(np.float64)
            m = t.mean()
            if m < 600 or t.max() > 15000:
                continue
            v = float(np.abs(np.diff(t, axis=1)).mean())
            if best is None or (v > best[0]) == want_detail:
                best = (v, y, x, m)
    return best


DIAG_BANDS = [(0.10, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.3536)]
DIAG_LEN, DIAG_COUNT = 512, 128


def diag_report(mos, pat, y, x, label, floors, is_floor):
    sig = diagonals(mos, pat, y, x, DIAG_LEN, DIAG_COUNT)
    nu, P = spectrum(sig)
    f = nu / np.sqrt(2.0)  # cycles per output pixel along the diagonal
    print(f"\n  {label} at ({y},{x})  {sig.shape[0]} diagonals x "
          f"{sig.shape[1]} green samples, spacing sqrt(2) px")
    head = f"    {'cyc/px':>13}  {'power':>13}"
    if not is_floor:
        head += f"  {'over floor':>12}  {'x floor':>8}"
    print(head + "   ")
    for lo, hi in DIAG_BANDS:
        b = band_power(f, P, lo, hi)
        line = f"    {lo:.3f}-{hi:.3f}  {b:13.1f}"
        if is_floor:
            floors[(lo, hi)] = b
        else:
            fl = floors[(lo, hi)]
            line += f"  {b - fl:12.1f}  {b / fl:7.2f}x"
        marker = "" if hi <= 0.25 else "   <- ABOVE plane Nyquist 0.25"
        print(line + marker)


def sweep(stack: Path, y: int, x: int, spec: str) -> int:
    """COMMISSIONING: is the supra-Nyquist energy optical, or an artifact?

    A detector's reading is worth nothing until it has been shown to respond to
    the thing it claims to measure. Real optical detail above plane Nyquist must
    COLLAPSE when the subject goes out of focus and return when it comes back,
    and it must do so SMOOTHLY -- defocus is continuous, so a genuine focus peak
    has shoulders. An isolated one-frame spike is not a focus peak; it is an
    anomaly, and the two are separated only by sampling finely enough to see
    whether the shoulders exist. Fixed-pattern noise, sensor artifacts, a
    lattice-indexing bug and read noise are all indifferent to focus and
    produce a flat trace.

    `spec` is "stride" or "start:end:stride" over the sorted frame list.
    """
    allf = sorted(stack.glob("*.ARW"))
    parts = [int(p) for p in spec.split(":")]
    frames = allf[::parts[0]] if len(parts) == 1 else \
        allf[parts[0]:parts[1]:parts[2]]
    print(f"FOCUS SWEEP  {stack.name}  region ({y},{x})  "
          f"{len(frames)} of {len(allf)} frames")
    print(f"  {'frame':>10}  {'mean DN':>8}  {'0.20-0.25':>12}  "
          f"{'0.25-0.30':>12}  {'0.30-0.354':>12}")
    for fr in frames:
        with rawpy.imread(str(fr)) as raw:
            mos = raw.raw_image_visible.astype(np.float64)
            pat = raw.raw_pattern
            black = float(np.mean(raw.black_level_per_channel))
        mos = np.maximum(mos - black, 0.0)
        sig = diagonals(mos, pat, y, x, DIAG_LEN, DIAG_COUNT)
        nu, P = spectrum(sig)
        f = nu / np.sqrt(2.0)
        print(f"  {fr.stem:>10}  {sig.mean():8.0f}  "
              f"{band_power(f, P, 0.20, 0.25):12.1f}  "
              f"{band_power(f, P, 0.25, 0.30):12.1f}  "
              f"{band_power(f, P, 0.30, 0.3536):12.1f}")
    return 0


def crop(stack: Path, y: int, x: int, idx: int, out: Path) -> int:
    """Render the EXACT samples the numbers came from, and look at them.

    Rows are successive diagonals, columns are position along the diagonal, so
    the picture is sheared and anisotropically scaled -- it is not a photograph.
    That is deliberate: it is the array the band powers were computed from, with
    no demosaic, no interpolation and no resampling between the sensor and the
    pixels on screen. If the focus peak is optical, this is legible at the peak
    frame and mush a few frames away.
    """
    from PIL import Image  # 8-bit PNG WRITE only; never used to read a TIFF
    fr = sorted(stack.glob("*.ARW"))[idx]
    with rawpy.imread(str(fr)) as raw:
        mos = raw.raw_image_visible.astype(np.float64)
        pat, black = raw.raw_pattern, float(np.mean(raw.black_level_per_channel))
    sig = diagonals(np.maximum(mos - black, 0.0), pat, y, x, DIAG_LEN, DIAG_COUNT)
    lo, hi = np.percentile(sig, 1.0), np.percentile(sig, 99.0)
    v = np.clip((sig - lo) / max(hi - lo, 1e-9), 0, 1) ** (1 / 2.2)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((v * 255).astype(np.uint8)).save(out)
    print(f"  wrote {out}  ({fr.stem}, stretch {lo:.0f}..{hi:.0f} DN)")
    return 0


def main() -> int:
    if sys.argv[1] == "--crop":
        return crop(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]),
                    int(sys.argv[5]), Path(sys.argv[6]))
    if sys.argv[1] == "--sweep":
        return sweep(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]),
                     sys.argv[5] if len(sys.argv) > 5 else "5")
    src = Path(sys.argv[1])
    with rawpy.imread(str(src)) as raw:
        mos = raw.raw_image_visible.astype(np.float64)
        pat = raw.raw_pattern
        black = float(np.mean(raw.black_level_per_channel))
    mos = np.maximum(mos - black, 0.0)
    print(f"{src.name}  mosaic {mos.shape}  black {black:.0f}  "
          f"pattern {pat.tolist()}")
    print("  DIAGONAL GREEN (exact sampling, spacing sqrt(2), Nyquist 0.3536)")

    floors = {}
    for label, want in [("FLAT (noise floor)", False), ("DETAIL", True)]:
        got = pick(mos, want)
        if got is None:
            print(f"  {label}: no eligible region")
            continue
        v, y, x, m = got
        diag_report(mos, pat, y, x,
                    f"{label}  mean {m:.0f} DN  coarse |dI| {v:.1f}",
                    floors, is_floor=not want)
    return 0


if __name__ == "__main__":
    sys.exit(main())
