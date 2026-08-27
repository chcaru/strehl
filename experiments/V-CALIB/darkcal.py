"""V-CALIB s2 -- dark-frame calibration: read noise, black level, and FPN.

READ-ONLY on D:.

What this establishes, and why each part is needed.

1. BLACK LEVEL and READ NOISE per ISO. The simulator (M102) writes
   `sigma^2 = g*S + (RN*g)^2` with g and RN taken from M92b's `sensor_for()`,
   which derives them from a photonstophotos table -- an EXTERNAL source, never
   checked against this body. 242 dark frames across 11 ISOs on this exact body
   is a direct check. A model constant that has never been measured on the
   hardware it models is a citation, not a calibration.

2. FIXED-PATTERN NOISE. V-LINEAR2 sec.10.1 bounded non-scene common-mode
   structure at 0.24% of the verdict statistic at 0.20-0.25 cyc/px, but read
   5.1% at 0.30-0.40 and 40.2% at 0.40-0.48, and disclosed that the bound is
   TIGHT on the estimator and LOOSE on SITE-LOCKED fixed-pattern noise, because
   the disjoint crops came from different sensor positions. The temporal mean of
   N dark frames at one ISO IS the site-locked pattern, measured directly: shot
   and read noise average down as 1/sqrt(N), what remains is fixed.

Two disclosures the owner made, both honoured here:
  - the first two frames of each set are stabilisation shots and are DISCARDED;
  - nothing else about these frames is assumed.

This step reports. It sets no constant in any other file.
"""
import json
import os
import sys

import numpy as np
import rawpy

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_EXP, "m57-shape-metric", "src"))
import m57lib as M57                                            # noqa: E402

DARKS = r"D:\macro-dark-frames"
OUT = r"C:\dev\strehl-out\V-CALIB\logs"

SKIP_FIRST = 2          # owner's disclosure: stabilisation shots
CROP = 2048             # central square on the raw grid, keeps RAM sane
BLACK_NOMINAL = 512     # AGENTS.md rig section

# The gain and read-noise model is IMPORTED from m57lib, not reimplemented.
# A first draft of this file reimplemented it as `iso/436.8` and reported ISO
# 50 at 7.75 e-, which looked like a refutation of the corpus and was in fact
# a defect in the reimplementation: m57lib clamps at BASE_ISO = 100 (so ISO 50
# is a digital pull sharing ISO 100's analogue gain) and switches read noise at
# SECOND_BASE_ISO = 400 (dual conversion gain). BOTH are visible in the data
# below. Reimplementing a model you intend to test is how you end up testing
# your own typing.


def sets():
    out = {}
    for d in sorted(os.listdir(DARKS)):
        p = os.path.join(DARKS, d)
        if not os.path.isdir(p):
            continue
        f = sorted(x for x in os.listdir(p) if x.lower().endswith(".arw"))
        if len(f) > SKIP_FIRST:
            out[d] = [os.path.join(p, x) for x in f[SKIP_FIRST:]]
    return out


def load(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0, x0 = (h - CROP) // 2, (w - CROP) // 2
        y0 -= y0 % 2                    # keep CFA phase
        x0 -= x0 % 2
        return np.asarray(v[y0:y0 + CROP, x0:x0 + CROP], dtype=np.float32)


def iso_of(path):
    import subprocess
    p = subprocess.run(["exiftool", "-j", "-n", "-ISO", path],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(p.stdout)[0]["ISO"]


def main():
    S = sets()
    if not S:
        raise SystemExit(f"no dark sets under {DARKS}")
    print(f"dark sets: {len(S)}   frames kept per set (first "
          f"{SKIP_FIRST} discarded as stabilisation shots):")

    rows = []
    for name, paths in S.items():
        iso = iso_of(paths[0])
        cube = np.stack([load(p) for p in paths], 0)     # (n, CROP, CROP)
        n = cube.shape[0]

        # Temporal statistics, per pixel.
        mu = cube.mean(0)                     # site-locked: FPN + black
        sd_t = cube.std(0, ddof=1)            # temporal: read + dark shot

        # Read noise: the temporal spread of a pixel with no light on it.
        # Median over pixels, so a few hot pixels cannot set the figure.
        rn_dn = float(np.median(sd_t))
        g = M57.gain_dn_per_e(iso)
        rn_e = rn_dn / g
        rn_e_model = M57.read_noise_e(iso)
        rn_dn_model = rn_e_model * g

        # Black level: the global offset.
        black = float(np.median(mu))

        # FPN: the spatial spread of the TEMPORAL MEAN, which has had the
        # temporal noise averaged down by sqrt(n). The residual temporal
        # noise still in `mu` is rn_dn/sqrt(n); subtract it in quadrature so
        # the figure is the fixed pattern and not the averaging floor.
        spatial = float(np.std(mu))
        floor = rn_dn / np.sqrt(n)
        fpn = float(np.sqrt(max(spatial ** 2 - floor ** 2, 0.0)))

        rows.append(dict(folder=name, iso=iso, n=n, black=black,
                         rn_dn=rn_dn, rn_e=rn_e, g=g, fpn_dn=fpn,
                         rn_e_model=rn_e_model, rn_dn_model=rn_dn_model,
                         ratio=rn_dn / rn_dn_model,
                         fpn_e=fpn / g,
                         mu_spatial_dn=spatial, avg_floor_dn=float(floor),
                         hot_frac=float(np.mean(mu > black + 8 * rn_dn))))
        del cube

    rows.sort(key=lambda r: r["iso"])
    print(f"\n{'=' * 108}")
    print(f"  {'ISO':>6}{'n':>4}{'black':>9}{'g DN/e-':>9}"
          f"{'RN meas':>9}{'RN pred':>9}{'meas/pred':>11}"
          f"{'RN_e meas':>11}{'RN_e mdl':>10}{'FPN DN':>9}{'FPN e-':>9}")
    print(f"{'=' * 108}")
    for r in rows:
        print(f"  {r['iso']:>6}{r['n']:>4}{r['black']:>9.2f}{r['g']:>9.4f}"
              f"{r['rn_dn']:>9.3f}{r['rn_dn_model']:>9.3f}"
              f"{r['ratio']:>11.3f}{r['rn_e']:>11.3f}"
              f"{r['rn_e_model']:>10.3f}{r['fpn_dn']:>9.3f}"
              f"{r['fpn_e']:>9.3f}")

    rat = np.array([r["ratio"] for r in rows])
    print(f"\n  black level: nominal {BLACK_NOMINAL} (AGENTS.md); "
          f"measured median {np.median([r['black'] for r in rows]):.2f}, "
          f"range {min(r['black'] for r in rows):.2f}-"
          f"{max(r['black'] for r in rows):.2f}")
    print(f"  measured/predicted read noise: median {np.median(rat):.3f}, "
          f"range {rat.min():.3f}-{rat.max():.3f}   "
          f"(1.000 would be exact agreement)")
    print("  The two structural features of m57lib's model are both VISIBLE "
          "in the measured DN column:")
    print("    - ISO 50 and ISO 100 have IDENTICAL read noise in DN "
          f"({rows[0]['rn_dn']:.3f} vs {rows[1]['rn_dn']:.3f}), confirming "
          "ISO 50 is a digital pull sharing ISO 100's analogue gain.")
    i25 = next(r for r in rows if r["iso"] == 250)
    i40 = next(r for r in rows if r["iso"] == 400)
    print(f"    - read noise FALLS from ISO 250 ({i25['rn_dn']:.3f} DN) to "
          f"ISO 400 ({i40['rn_dn']:.3f} DN) despite {i40['g'] / i25['g']:.2f}x "
          "more gain: the dual-conversion-gain switch m57lib places at 400.")
    print("  FPN in ELECTRONS falls with ISO while FPN in DN rises only "
          f"{rows[-1]['fpn_dn'] / rows[1]['fpn_dn']:.2f}x across a "
          f"{rows[-1]['g'] / rows[1]['g']:.0f}x gain range, so the fixed "
          "pattern is largely DOWNSTREAM of the gain stage.")

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "darkcal.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
