"""Audit every master this lane measured on for the HEAD auto-exposure clipping
regression (ORCH broadcast 2026-08-27).

The broadcast asks which of three cases each lane is in.  Reading my render
scripts answers it in one grep -- every V-DRIFT render is `--linear-srgb
--demosaic` with no `--auto-exposure`.  But this lane has already been burnt
once tonight by exactly that move: two merge changes READ as default-off from
source and changed every render when measured.  So this script does not read
flags.  It opens the actual pixels of the actual files the conclusions were
drawn from and counts how many sit at the ceiling.

Reported per file: fraction of samples at the 16-bit ceiling, the median, and
the 99.9th percentile.  A blown master per the broadcast's own threshold is
>25% clipped; a catastrophic one has a pure-white median.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\V-DRIFT\clipaudit.json")

# The two lanes' output trees.  V-SPEED arm 1 used the shipping recipe
# `--srgb --auto-exposure` on the PIN binary; V-DRIFT used `--linear-srgb
# --demosaic` on both pin and HEAD.  Both are audited, because the claim under
# test is about pixels, not about which flags I believe I passed.
ROOTS = [
    (Path(r"C:\dev\strehl-out\V-SPEED"), "V-SPEED"),
    (Path(r"C:\dev\strehl-out\V-DRIFT"), "V-DRIFT"),
]

# Intermediates, not masters: `aligned/` holds align_image_stack output and
# `tif*/` holds the dcraw conversions that feed the enfuse and focus-stack arms.
# Auditing those answers a question nobody asked and costs ~300 large reads.
SKIP_DIRS = {"aligned", "tif", "tif-srgb", "pilot-tif"}


def ceiling(a):
    """The saturation value for this array's dtype.

    Guarding this rather than hardcoding 65535: a float render saturates at
    1.0 and would report 0% clipped against a 65535 test, which is the silent
    always-clean answer.
    """
    if a.dtype == np.uint16:
        return 65535.0
    if a.dtype == np.uint8:
        return 255.0
    if np.issubdtype(a.dtype, np.floating):
        return 1.0
    raise SystemExit(f"unhandled dtype {a.dtype}")


def audit(p):
    a = tifffile.imread(str(p))
    hi = ceiling(a)

    # CHANNEL DEFECT, CAUGHT BY THE DATA.  The first run of this script called
    # ten enfuse masters BLOWN at 25.04% and 25.02%.  Both are 1/4 of samples
    # to two decimals, which is not a highlight distribution -- it is an
    # opaque alpha channel.  enfuse writes RGBA; alpha is 65535 everywhere;
    # counting samples across all four channels therefore hands every enfuse
    # master a free 25.000% and pushes it over the broadcast's own 25%
    # "BLOWN" threshold on an empty channel.  The linear master `r1-enfuse`
    # settles it: exactly 25.000%, i.e. the alpha and nothing else.
    #
    # Clipping is a property of the colour channels, so measure it there and
    # carry alpha separately rather than silently dropping a channel.
    alpha = None
    if a.ndim == 3 and a.shape[2] == 4:
        alpha = round(100.0 * float((a[:, :, 3] >= hi).mean()), 4)
        a = a[:, :, :3]

    if a.dtype == np.uint16:
        # Exact, and it never materialises a float copy.  The float64 route
        # allocates 4x the file and np.median sorts it; on 200 MB masters that
        # thrashed a saturated host badly enough to be unusable.  A 65536-bin
        # histogram gives the same median and the same clip count for integer
        # data, by construction rather than by approximation.
        h = np.bincount(a.reshape(-1), minlength=65536).astype(np.int64)
        n = int(h.sum())
        c = np.cumsum(h)
        med = float(np.searchsorted(c, (n + 1) // 2))
        p999 = float(np.searchsorted(c, int(n * 0.999)))
        clip = 100.0 * float(h[65535]) / n
    else:
        f = a.astype(np.float64)
        med = float(np.median(f))
        p999 = float(np.percentile(f, 99.9))
        clip = 100.0 * float((f >= hi).mean())
    return {
        "path": str(p),
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "clipped_pct": round(clip, 4),
        "alpha_clipped_pct": alpha,
        "median": round(med, 1),
        "p999": round(p999, 1),
        "ceiling": hi,
    }


def commission():
    """A clip counter that cannot see a clipped image is the whole risk here.

    Two plants, both signs.  A synthesised all-ceiling frame must read 100%,
    and a synthesised ramp that never reaches the ceiling must read 0%.  A
    counter that returned a constant would fail one of these.
    """
    import tempfile

    ok, fail = 0, []
    with tempfile.TemporaryDirectory() as td:
        blown = Path(td) / "blown.tif"
        tifffile.imwrite(str(blown), np.full((64, 64), 65535, np.uint16))
        r = audit(blown)
        if r["clipped_pct"] == 100.0 and r["median"] == 65535.0:
            ok += 1
        else:
            fail.append(f"all-ceiling frame read {r['clipped_pct']}% / med {r['median']}")

        clean = Path(td) / "clean.tif"
        ramp = np.linspace(0, 65534, 64 * 64).reshape(64, 64).astype(np.uint16)
        tifffile.imwrite(str(clean), ramp)
        r = audit(clean)
        if r["clipped_pct"] == 0.0:
            ok += 1
        else:
            fail.append(f"sub-ceiling ramp read {r['clipped_pct']}% clipped")

        # A partial plant, because 0% and 100% are both reachable by a
        # degenerate counter (always-min, always-max).  Half the pixels at the
        # ceiling must read as half.
        half = Path(td) / "half.tif"
        h = np.full((64, 64), 1000, np.uint16)
        h[:32] = 65535
        tifffile.imwrite(str(half), h)
        r = audit(half)
        if abs(r["clipped_pct"] - 50.0) < 1e-6:
            ok += 1
        else:
            fail.append(f"half-ceiling frame read {r['clipped_pct']}%")

        # An RGBA frame with opaque alpha and CLEAN colour must read 0%, not
        # 25%.  This is the defect the corpus caught; without a plant for it
        # the fix is unverified.  The converse plant matters just as much: an
        # RGBA frame whose COLOUR is blown must still read 100%, or "exclude
        # alpha" could have been implemented as "ignore 4-channel files".
        rgba = Path(td) / "rgba.tif"
        q = np.zeros((64, 64, 4), np.uint16)
        q[:, :, :3] = 1000
        q[:, :, 3] = 65535
        tifffile.imwrite(str(rgba), q)
        r = audit(rgba)
        if r["clipped_pct"] == 0.0 and r["alpha_clipped_pct"] == 100.0:
            ok += 1
        else:
            fail.append(f"opaque-alpha clean RGBA read {r['clipped_pct']}% "
                        f"colour / {r['alpha_clipped_pct']}% alpha")

        rgba2 = Path(td) / "rgba2.tif"
        q2 = np.full((64, 64, 4), 65535, np.uint16)
        tifffile.imwrite(str(rgba2), q2)
        r = audit(rgba2)
        if r["clipped_pct"] == 100.0:
            ok += 1
        else:
            fail.append(f"blown RGBA colour read {r['clipped_pct']}%")

    for m in fail:
        print(f"  [FAIL] {m}")
    print(f"commission: {ok}/5 " + ("PASS" if not fail else "FAIL"))
    return not fail


def main():
    if "--commission" in sys.argv:
        raise SystemExit(0 if commission() else 1)

    if not commission():
        raise SystemExit("clip counter failed commissioning; refusing to audit")

    roots = list(ROOTS)
    if "--src" in sys.argv:
        d = Path(sys.argv[sys.argv.index("--src") + 1])
        roots = [(d, d.name)]

    rows = []
    for root, lane in roots:
        if not root.is_dir():
            print(f"  (absent) {root}")
            continue
        for p in sorted(root.rglob("*.tif")) + sorted(root.rglob("*.tiff")):
            if any(d in SKIP_DIRS for d in p.parts):
                continue
            try:
                r = audit(p)
            except Exception as e:  # noqa: BLE001 -- report, do not abort the sweep
                print(f"  [skip] {p.name}: {e}")
                continue
            r["lane"] = lane
            rows.append(r)
            print(f"  {r['clipped_pct']:8.3f}% med {r['median']:8.1f}  {p.name}",
                  flush=True)

    rows.sort(key=lambda r: -r["clipped_pct"])
    print(f"\n{'lane':8} {'clip%':>8} {'median':>9} {'p99.9':>9}  file")
    for r in rows:
        print(f"{r['lane']:8} {r['clipped_pct']:8.3f} {r['median']:9.1f} "
              f"{r['p999']:9.1f}  {Path(r['path']).name}")

    blown = [r for r in rows if r["clipped_pct"] > 25.0]
    print(f"\n{len(rows)} masters audited, {len(blown)} BLOWN (>25% at ceiling)")
    for r in blown:
        print(f"  BLOWN {r['clipped_pct']:.2f}%  {r['path']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
