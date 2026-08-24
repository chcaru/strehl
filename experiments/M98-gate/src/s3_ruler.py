"""M98 S3 -- the external anchor.

`highly-angled-ruler-mm-cpl` is 299 frames of a millimetre ruler at a steep
angle.  The tick pitch is known a priori and is a *physical* scale, so the
modulation of the tick comb is a resolved-detail measurement that does not
depend on any metric this project invented.  That is the point: neither `dsig`
nor HF amplitude is ground truth, and the adjudication needs something outside
both.

Metric, pre-registered (PREREG S3):

  For each ROI, the 2-D power spectrum of the Hann-windowed green plane is
  searched for its dominant non-DC peak.  On a ruler that peak IS the tick
  comb; its radius `f0` is the comb frequency in cyc/px and its angle is the
  ruler's orientation, both read off the gate-0 render and then FROZEN.  At
  every gate the comb power `S` is integrated over a small disc at that fixed
  (f0, theta), and the local broadband floor `B` is integrated over identical
  discs at 0.82*f0 and 1.22*f0 along the same direction.

  Modulation      M = sqrt(max(S - B, 0))
  Reported        M(T)/M(0)

  The sideband subtraction is what makes this readable at all: the gate changes
  the noise floor by several fold, and an unsubtracted comb power would move
  with the floor rather than with the resolved detail.

  INERT gate (rule 13, and PREREG's registered guard): an ROI is admitted only
  if S/B >= 3 on the gate-0 render.  An ROI whose comb does not clear its own
  sidebands cannot express a change in comb modulation, and reporting a ratio
  from it would be reporting noise.

  The 2nd harmonic (2*f0, same theta) is reported as a second, strictly harder
  probe: a square-ish tick profile puts real power there, and it sits at twice
  the frequency, so it is where a blur difference shows first.

The ruler is in `align_cmd.rs`'s TILTED_SUBJECTS, so `strehl stack` renders it
UNREGISTERED and writes no sidecar.  That is stated in the report; it makes the
ruler an unaligned arm by construction, which is the correct comparator for
M85's pre-alignment ladder and a limit on transferring the result to bee-3-cpl.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m98lib as M98

OUT = Path(__file__).resolve().parent.parent / "out"
GATES = [0.0, 0.5, 1.0, 2.0, 4.0]

# Frozen geometry of the probe.
DISC = 2.0  # bins
SIDE_LO, SIDE_HI = 0.82, 1.22
F_MIN, F_MAX = 0.03, 0.40  # plausible comb band, cyc/px
INERT_MIN = 3.0  # S/B on the gate-0 render


def ruler_path(gate: float) -> Path:
    return Path(r"C:\dev\strehl-out\M98\renders") / (RENDER_FMT % f"{gate:g}")


STACK = sys.argv[1] if len(sys.argv) > 1 else "highly-angled-ruler-mm-cpl"
if STACK == "highly-angled-ruler-mm-cpl":
    RENDER_FMT = "ruler-g%s.tif"
    TAG, REG = "highly-angled-ruler-mm-cpl", "UNREGISTERED (tilted subject, M86)"
else:
    RENDER_FMT = STACK + "-FULL-ALN-g%s.tif"
    TAG, REG = STACK, "REGISTERED (alignment ON, one shared sidecar)"


def hann2(n: int) -> np.ndarray:
    w = np.hanning(n)
    return np.outer(w, w)


def power(img: np.ndarray) -> np.ndarray:
    a = img.astype(np.float64)
    a = a - a.mean()
    a *= hann2(a.shape[0]) if a.shape[0] == a.shape[1] else 1.0
    F = np.fft.fftshift(np.fft.fft2(a))
    return (F.real**2 + F.imag**2) / a.size


def freq_grid(n: int):
    f = np.fft.fftshift(np.fft.fftfreq(n))
    fy, fx = np.meshgrid(f, f, indexing="ij")
    return fy, fx


def find_comb(P: np.ndarray):
    """Dominant non-DC spectral peak, returned as (fy, fx, f0, S/B)."""
    n = P.shape[0]
    fy, fx = freq_grid(n)
    r = np.hypot(fy, fx)
    band = (r >= F_MIN) & (r <= F_MAX)
    # Half-plane, so the peak and its conjugate are not both returned.
    half = (fy > 0) | ((np.abs(fy) < 1e-12) & (fx > 0))
    m = band & half
    if not m.any():
        return None
    idx = np.argmax(np.where(m, P, -np.inf))
    iy, ix = np.unravel_index(idx, P.shape)
    return float(fy[iy, ix]), float(fx[iy, ix]), float(r[iy, ix])


def disc_sum(P: np.ndarray, fy0: float, fx0: float) -> float:
    """Integrate `P` over a small disc at (fy0, fx0) and its conjugate."""
    n = P.shape[0]
    fy, fx = freq_grid(n)
    bin_w = 1.0 / n
    tot = 0.0
    for sy, sx in ((fy0, fx0), (-fy0, -fx0)):
        d = np.hypot(fy - sy, fx - sx) / bin_w
        tot += float(P[d <= DISC].sum())
    return tot


def probe(P: np.ndarray, fy0: float, fx0: float):
    """Comb power, sideband floor, and modulation at a fixed direction."""
    S = disc_sum(P, fy0, fx0)
    B = 0.5 * (
        disc_sum(P, fy0 * SIDE_LO, fx0 * SIDE_LO)
        + disc_sum(P, fy0 * SIDE_HI, fx0 * SIDE_HI)
    )
    M = np.sqrt(max(S - B, 0.0))
    return S, B, M


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = []

    def say(s=""):
        print(s)
        log.append(s)

    say("=" * 78)
    say(f"M98 S3 -- external anchor: {TAG}")
    say(f"  {REG}.  Tick pitch is a known physical scale, so comb")
    say("  modulation measures resolved detail against something neither M85")
    say("  nor M92 invented.")
    say("=" * 78)
    say()

    imgs = {}
    for g in GATES:
        p = ruler_path(g)
        if not p.exists():
            say(f"MISSING {p}")
            return
        imgs[g] = M98.green(p)
    h, w = imgs[0.0].shape
    say(f"render geometry : {w} x {h}")

    # Denser lattice than S1's: the ruler occupies only part of the field, and
    # only ROIs actually on the ruler can carry a comb.  384 px windows keep
    # the frequency resolution at 1/384 = 0.0026 cyc/px, far finer than the
    # 2-bin probe disc.
    rois = M98.roi_grid(h, w, n=384, cols=9, rows=6)
    say(f"ROI lattice     : {len(rois)} of 384^2")
    say()

    # --- freeze the comb on the gate-0 render, then apply the INERT gate ----
    frozen = []
    for k, xy in enumerate(rois):
        P0 = power(M98.crop(imgs[0.0], xy, 384))
        pk = find_comb(P0)
        if pk is None:
            continue
        fy0, fx0, f0 = pk
        S, B, _ = probe(P0, fy0, fx0)
        ratio = S / B if B > 0 else np.inf
        frozen.append(
            dict(k=k, xy=[int(xy[0]), int(xy[1])], fy=fy0, fx=fx0, f0=f0,
                 s_over_b=ratio, pitch_px=1.0 / f0 if f0 > 0 else np.nan)
        )

    live = [f for f in frozen if f["s_over_b"] >= INERT_MIN]
    say("--- INERT GATE (rule 13): comb must clear its own sidebands by 3x ---")
    say(f"  ROIs with a peak in [{F_MIN}, {F_MAX}] cyc/px : {len(frozen)}")
    say(f"  ROIs passing S/B >= {INERT_MIN}                     : {len(live)}")
    if live:
        sb = np.array([f["s_over_b"] for f in live])
        pp = np.array([f["pitch_px"] for f in live])
        say(f"  S/B on survivors : min {sb.min():.2f}  med {np.median(sb):.2f}"
            f"  max {sb.max():.2f}")
        say(f"  comb pitch (px)  : min {pp.min():.2f}  med {np.median(pp):.2f}"
            f"  max {pp.max():.2f}")
        say("  A steeply-angled mm ruler foreshortens, so pitch varying")
        say("  several-fold across the field is the expected signature, not a")
        say("  defect: it means the probe is riding the real comb.")
    if len(live) < 4:
        say("  INERT GATE RED -- fewer than 4 live ROIs, the ruler cannot")
        say("  express this measurement and no ratio is reported.")
        (OUT / f"s3_{STACK}.log").write_text("\n".join(log), encoding="utf-8")
        return
    say("  INERT GATE GREEN")
    say()

    # --- the ladder, at the frozen comb ------------------------------------
    HARM = (1, 2, 3, 4, 5, 6)
    rows = []
    for f in live:
        rec = dict(f)
        for hn in HARM:
            name = f"h{hn}"
            base = None
            for g in GATES:
                P = power(M98.crop(imgs[g], tuple(f["xy"]), 384))
                S, B, Mm = probe(P, f["fy"] * hn, f["fx"] * hn)
                rec[f"{name}_S_{g}"] = S
                rec[f"{name}_B_{g}"] = B
                rec[f"{name}_M_{g}"] = Mm
                if g == 0.0:
                    base = Mm
                    rec[f"{name}_sb0"] = S / B if B > 0 else np.inf
                rec[f"{name}_r_{g}"] = Mm / base if base and base > 0 else np.nan
        rows.append(rec)

    say("--- HARMONIC LADDER of the frozen comb -------------------------------")
    say("  The mm comb's fundamental sits far below the band the gate acts in,")
    say("  so the fundamental alone cannot express a tenth-pixel blur.  A tick")
    say("  is a narrow bar, so its harmonics carry real power at KNOWN")
    say("  frequencies -- n*f0 for the same physical pitch.  Each harmonic is")
    say("  admitted separately by the same INERT gate (S/B >= 3 at gate 0).")
    say()
    ruler_blur = {}
    for hn in HARM:
        name = f"h{hn}"
        use = [r for r in rows
               if r["f0"] * hn < 0.47 and r.get(f"{name}_sb0", 0) >= INERT_MIN]
        fq = [r["f0"] * hn for r in use]
        say(f"  harmonic n={hn}: {len(use)}/{len(rows)} ROIs live"
            + (f", f = {min(fq):.4f}-{max(fq):.4f} cyc/px" if use else ""))
        if len(use) < 3:
            say("    INERT: fewer than 3 live ROIs, not reported")
            say()
            continue
        say(f"    {'gate':>6} {'M(T)/M(0)':>12} {'SE':>9} {'sigma':>7} "
            f"{'n<1':>5} {'equiv blur px':>14} {'SE':>9}")
        for g in GATES:
            v = np.array([r[f"{name}_r_{g}"] for r in use], dtype=float)
            v = v[np.isfinite(v)]
            if v.size < 2:
                continue
            mean = float(v.mean())
            se = float(v.std(ddof=1) / np.sqrt(v.size))
            sig = abs(mean - 1.0) / se if se > 0 else float("nan")
            ss = []
            for r in use:
                rr = r[f"{name}_r_{g}"]
                q = r["f0"] * hn
                if not np.isfinite(rr) or rr <= 0:
                    continue
                val = -np.log(rr) / (2 * np.pi**2 * q**2)
                ss.append(np.sign(val) * np.sqrt(abs(val)))
            ss = np.array(ss, dtype=float)
            bm = float(ss.mean()) if ss.size else np.nan
            bs = float(ss.std(ddof=1) / np.sqrt(ss.size)) if ss.size > 1 else np.nan
            ruler_blur.setdefault(name, {})[str(g)] = dict(
                r=mean, r_se=se, px=bm, px_se=bs, n=int(v.size))
            say(f"    {g:>6} {mean:>12.5f} {se:>9.5f} {sig:>7.2f} "
                f"{int((v < 1.0).sum()):>5} {bm:>14.5f} {bs:>9.5f}")
        say()
    say("  Sign convention matches dsig: POSITIVE equiv blur = gate T BLURRIER.")

    (OUT / f"s3_{STACK}.log").write_text("\n".join(log), encoding="utf-8")
    (OUT / f"s3_{STACK}.json").write_text(
        json.dumps(dict(live=len(live), frozen=len(frozen), rows=rows,
                        blur=ruler_blur), indent=1, default=float),
        encoding="utf-8")
    say(f"\nwrote {OUT / ('s3_' + STACK + '.json')}")


if __name__ == "__main__":
    main()
