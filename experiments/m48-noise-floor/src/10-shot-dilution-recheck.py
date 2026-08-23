r"""M48 script 10 -- re-check script 08 after finding a use-after-free in it.

Script 09 crashed with an access violation (0xC0000005) because
`rawpy.RawPy.raw_image_visible` returns a VIEW into libraw's internal buffer,
which is freed when the context manager exits. Script 08 contains the same
defect in a quieter form: it copies `raw_image_visible` with `.astype()` (safe)
but binds `raw_colors_visible` WITHOUT copying (unsafe) and then indexes with it
after the `with` block has closed. That is a read of freed memory. It did not
crash, which is the worst outcome, because the numbers it produced are in the
M48 report as facts 25 and 28.

Rule 15: script 08 is not modified. This script re-measures the same quantity
with correct memory handling, so the two can be compared and script 08's
numbers either confirmed or corrected. It also adds the CFA-plane check that
script 08 assumed rather than verified: that colour indices 1 and 3 are the two
greens on this body.

Read-only with respect to all source directories.
"""

import json
import os

import numpy as np
import rawpy

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_OLD_HIGH = 1.47
RN_NEW_HIGH = 1.2392

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "shot-dilution-recheck.json")

STACKS = [
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1000.0, 3),
    ("113MSDCF", r"D:\personal\macro\113MSDCF", 500.0, 3),
    ("119MSDCF-placebo", r"C:\dev\macro\test\119MSDCF", 50.0, 2),
]


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise(iso, high_value):
    return high_value if iso >= SECOND_BASE_ISO else RN_LOW


def sigma(signal_dn, g, rn_e):
    s = np.maximum(signal_dn, 0.0)
    read_dn = rn_e * g
    return np.sqrt(g * s + read_dn * read_dn)


def green_luma(path):
    """Black-subtracted green luma per 2x2 site, in DN. Everything that touches
    libraw's buffers stays inside the `with` block, and both arrays are copied."""
    with rawpy.imread(path) as raw:
        img = raw.raw_image_visible.astype(np.float64)
        colors = np.array(raw.raw_colors_visible, copy=True)  # COPY, not a view
        black = np.array(raw.black_level_per_channel, dtype=np.float64)
        desc = raw.color_desc.decode() if hasattr(raw, "color_desc") else "?"
    h, w = img.shape
    h -= h % 2
    w -= w % 2
    img = img[:h, :w]
    colors = colors[:h, :w]
    sub = img - black[colors]
    q = sub.reshape(h // 2, 2, w // 2, 2)
    qc = colors.reshape(h // 2, 2, w // 2, 2)
    g_mask = (qc == 1) | (qc == 3)
    n = g_mask.sum(axis=(1, 3))
    tot = (q * g_mask).sum(axis=(1, 3))
    # Verify the assumption script 08 made silently: exactly two greens per site.
    counts = np.unique(n)
    return np.where(n > 0, tot / np.maximum(n, 1), 0.0), desc, counts.tolist()


def main():
    results = []
    for label, d, iso, nframes in STACKS:
        files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))[:nframes]
        g = gain(iso)
        high = iso >= SECOND_BASE_ISO
        rn_old, rn_new = read_noise(iso, RN_OLD_HIGH), read_noise(iso, RN_NEW_HIGH)

        parts, desc, counts = [], None, None
        for f in files:
            lum, desc, counts = green_luma(os.path.join(d, f))
            parts.append(lum.ravel())
        s = np.concatenate(parts)

        r = sigma(s, g, rn_new) / sigma(s, g, rn_old)
        shift = np.abs(1.0 / r - 1.0)
        results.append(
            {
                "stack": label,
                "iso": iso,
                "high_gain_mode": bool(high),
                "cfa_desc": desc,
                "greens_per_site": counts,
                "n_pixels": int(s.size),
                "signal_dn_median": float(np.median(s)),
                "signal_dn_p0_1": float(np.percentile(s, 0.1)),
                "response_shift_mean_pct": float(shift.mean() * 100.0),
                "response_shift_median_pct": float(np.median(shift) * 100.0),
                "response_shift_p99_pct": float(np.percentile(shift, 99) * 100.0),
                "frac_pixels_shift_over_1pct": float((shift > 0.01).mean()),
                "shot_equals_read_at_dn": float(rn_old * rn_old * g),
                "frac_pixels_below_crossover": float((s < rn_old * rn_old * g).mean()),
            }
        )
        print(
            f"{label:18} ISO {iso:6.0f}  CFA={desc}  greens/site={counts}  "
            f"median S = {np.median(s):8.1f} DN  p0.1 = {np.percentile(s,0.1):7.1f}  "
            f"mean |1/r-1| = {shift.mean()*100:6.3f}%  "
            f"p99 = {np.percentile(shift,99)*100:6.3f}%"
        )

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "_meta": {
                    "script": "10-shot-dilution-recheck.py",
                    "purpose": "re-measure script 08 with correct rawpy memory "
                    "handling; script 08 read raw_colors_visible after "
                    "the context manager freed it",
                },
                "stacks": results,
            },
            fh,
            indent=2,
        )
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
