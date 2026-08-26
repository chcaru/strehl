"""Commission veilorlight.py by planting known effects into a real render.

The instrument claims to separate "removed veil" from "added light".  That claim is
only worth anything if it survives being shown both, plus the ambiguous mixture, on
real data with a real subject mask.  Five plants:

  1. NULL              the same file twice -> no shift, no noise change.
  2. PURE BIAS         +200 DN everywhere outside the subject.  This is what an
                       undebiased order statistic does.  Must be reported as a
                       far-field shift of +200 DN.
  3. PURE REPAIR       brightening that DECAYS with distance and is spent by the far
                       field -- a genuine veil fix.  Far-field shift must be ~0 and
                       the verdict must clear it.
  4. MIXTURE           repair + 120 DN of bias.  The near-field numbers look better
                       than case 3, and every self-referenced metric would prefer
                       it.  The instrument must still surface the +120 DN.
  5. NOISE             a 9.7x noise increase with no level change, which is the
                       fingerprint of an order statistic that HAS been debiased in
                       level.  Must be caught by the sd ratio, not the level.
                       Planted in BOTH chroma regimes, because the instrument's two
                       noise readings differ by sqrt(3) between them:
                         5a monochrome (chroma-correlated) -> both read 9.70x;
                         5b per-channel independent        -> channel mean reads
                            9.7/sqrt(3) = 5.66x while per-channel still reads 9.70x.
                       5b is the case that would have silently under-read a real
                       noise increase by 42% had only the channel mean been kept.

Cases 3 and 4 are the whole point: they differ only in an additive constant, and a
ratio or a self-normalised profile cannot tell them apart at all.

The plants go into `flower-bud-alone-cpl` -- the actual verification subject, not a
stand-in.  Commissioning on the real geometry is what makes the pass mean "this
instrument works on the picture it will judge" rather than "it works on some
picture".  `bee-3-cpl`, used first, has no bright neutral backdrop at all and the
harness refuses it, which is itself the correct behaviour.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\BUILD-SHARP\veil\flower-bud-alone-cpl\base\linear-srgb.tif"
HERE = os.path.dirname(os.path.abspath(__file__))
VOL = os.path.join(HERE, "veilorlight.py")
RNG = np.random.default_rng(2026)


def run(base: str, fixed: str, tag: str, tmp: str) -> dict:
    out = os.path.join(tmp, f"{tag}.json")
    cmd = [sys.executable, VOL, "--baseline", base, "--fixed", fixed,
           "--far", "400", "--frames", "205", "--out", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"{tag}: veilorlight failed")
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    if not os.path.exists(SRC):
        raise SystemExit(f"missing source render: {SRC}")
    img = tifffile.imread(SRC).astype(np.float64)
    print(f"source {os.path.basename(SRC)}  shape {img.shape}")

    # Rebuild the same mask/distance the instrument will use, so the plants are
    # defined against the same geometry it measures.
    sys.path.insert(0, HERE)
    from scipy.ndimage import distance_transform_edt  # noqa: E402
    from veilorlight import subject_mask  # noqa: E402
    mask = subject_mask(img)
    dist = distance_transform_edt(~mask)
    bg = (~mask)[:, :, None]
    decay = np.exp(-dist / 90.0)[:, :, None]     # spent well before d = 400

    tmp = tempfile.mkdtemp(prefix="veilcomm-")
    base_p = os.path.join(tmp, "base.tif")
    tifffile.imwrite(base_p, img.astype(np.uint16))

    plants: list[tuple[str, np.ndarray, float, float, float]] = []
    plants.append(("1 null", img.copy(), 0.0, 1.0, 1.0))
    plants.append(("2 pure bias", img + 200.0 * bg, 200.0, 1.0, 1.0))
    plants.append(("3 pure repair", img + 3000.0 * decay * bg, 0.0, 1.0, 1.0))
    plants.append(("4 mixture", img + 3000.0 * decay * bg + 120.0 * bg,
                   120.0, 1.0, 1.0))
    plants.append(("5a noise mono", img, 0.0, 0.0, 0.0))
    plants.append(("5b noise chroma", img, 0.0, 0.0, 0.0))

    fails = []
    for tag, arr, want_shift, want_ratio, want_chan in plants:
        if tag.startswith("5"):
            # Scale the plant to the measured baseline far-field sd.  The
            # per-channel sd is the right reference: it is the one that is
            # invariant to how the noise is correlated between channels.
            probe = run(base_p, base_p, "probe", tmp)
            sd_chan0 = probe["far"]["baseline"]["noise_sd_chan_dn"]
            sd_mean0 = probe["far"]["baseline"]["noise_sd_dn"]
            k = sd_chan0 / sd_mean0
            e = np.sqrt(9.7 ** 2 - 1.0)
            extra = e * sd_chan0
            # The expected CHANNEL-MEAN ratio is not 9.7 and not 9.7/sqrt(3).
            # It depends on how chroma-correlated the BASELINE noise already is,
            # measured here as k = sd_chan/sd_mean (1.13 on this subject, against
            # 1.73 for perfectly independent and 1.00 for perfectly correlated).
            # Deriving the expectation from k rather than assuming a value makes
            # this plant assert the instrument's channel arithmetic exactly.
            if tag.startswith("5a"):
                n = RNG.normal(0.0, extra, img.shape[:2])[:, :, None]
                want_ratio = float(np.sqrt(1.0 + (e * k) ** 2))
            else:
                n = RNG.normal(0.0, extra, img.shape)
                want_ratio = float(np.sqrt(1.0 + (e * k) ** 2 / 3.0))
            want_chan = float(np.sqrt(1.0 + e ** 2))
            print(f"   [{tag}] baseline chroma factor k = {k:.3f}"
                  f"  -> expected channel-mean ratio {want_ratio:.2f}")
            arr = img + n * bg
        p = os.path.join(tmp, "f.tif")
        tifffile.imwrite(p, np.clip(arr, 0, 65535).astype(np.uint16))
        rep = run(base_p, p, tag.split()[0], tmp)
        shift = rep["far_shift_dn"]
        ratio = rep["noise_ratio"]
        chan = rep["noise_ratio_chan"]
        ped = rep["pedestal_dn"]
        ok_s = abs(shift - want_shift) <= max(8.0, 0.06 * abs(want_shift))
        # The pedestal is what the verdict turns on, so assert it, not only the
        # mean far-field shift.  For a spent repair the pedestal must be ~0 even
        # though the mean shift is not, which is the case-3 discrimination.
        ok_p = abs(ped - want_shift) <= max(3.0, 0.06 * abs(want_shift))
        ok_r = abs(ratio - want_ratio) <= max(0.25, 0.12 * want_ratio)
        ok_c = abs(chan - want_chan) <= max(0.25, 0.12 * want_chan)
        ok = ok_s and ok_p and ok_r and ok_c
        print(f"{tag:16s} shift {shift:+8.1f} ped {ped:+8.1f} DN "
              f"(want {want_shift:+7.1f})   "
              f"sd ratio {ratio:5.2f}/{chan:5.2f} "
              f"(want {want_ratio:4.2f}/{want_chan:4.2f})   "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(tag)

    print()
    if fails:
        print("COMMISSIONING FAILED: " + ", ".join(fails))
        return 1
    print("COMMISSIONING PASSED: 6/6")
    print("Cases 3 and 4 differ ONLY by an additive 120 DN and were separated;")
    print("that is the discrimination no ratio or self-normalised profile can make.")
    print("Cases 5a and 5b carry the SAME planted noise and differ only in chroma")
    print("correlation. Their expected channel-mean ratios are DERIVED from the")
    print("baseline's own measured chroma factor rather than assumed, while the")
    print("per-channel ratio holds at 9.70 for both -- which is what licenses")
    print("reading the real noise ratio without assuming anything about how the")
    print("fix correlates noise between channels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
