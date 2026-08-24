"""M104b step 0 -- choose the single frame every arm will be decoded from.

WHY A SINGLE FRAME.  The demosaic is the only stage that may differ between
arms.  Feeding a 79-frame merge into this would confound demosaic quality with
noise averaging, which is the confound M104 spent a whole phase separating.
So: one frame, decoded many ways.

WHY THIS IS A SELECTION HEURISTIC AND NOT A BAR.  The frame is chosen by comb
modulation on a HALF-SIZE (2x2 binned, undemosaiced) decode.  Binning is
common to every candidate frame, so the choice cannot favour any demosaic --
none has run yet.  The number this prints is not reported as a result and no
bar rests on it.

D: IS READ-ONLY.  This script opens files there and writes nothing; the size
and mtime of every entry is compared before and after.
"""

import json
import pathlib
import sys

import numpy as np
import rawpy

sys.path.insert(
    0,
    str(pathlib.Path(__file__).resolve().parents[2] / "M104-resample-verify" / "src"),
)
import m104lib as L  # noqa: E402

SRC = pathlib.Path(r"D:\personal\macro\flat-on-ruler-cpl")
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)


def snapshot():
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in SRC.iterdir()}


def half_green(path):
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(
            half_size=True,
            output_bps=16,
            gamma=(1, 1),
            no_auto_bright=True,
            use_camera_wb=True,
            output_color=rawpy.ColorSpace.raw,
            user_flip=0,
        )
    return rgb[..., 1].astype(np.float64)


def main():
    before = snapshot()
    frames = sorted(SRC.glob("*.ARW"))
    idx = list(range(0, len(frames), 4))
    rows = []
    for i in idx:
        g = half_green(frames[i])
        # Seed each frame from ITSELF.  seed_combs already refuses an ROI
        # whose comb is below S/B 3, so a defocused frame scores 0 by finding
        # no comb rather than by being judged against someone else's seed.
        seed = L.seed_combs(g, cols=3, rows=3)
        arm = L.measure_arm(g, seed, cols=3, rows=3)
        mods = [v["mod"] for v in arm.values() if v["sb"] >= L.INERT_MIN]
        score = float(np.median(mods)) if mods else 0.0
        rows.append({"i": i, "name": frames[i].name, "n_live": len(mods), "mod": score})
        print(f"  {frames[i].name}  live={len(mods):2d}  mod={score:.6g}", flush=True)

    assert snapshot() == before, "READ-ONLY ASSERTION FAILED on D:"
    print("read-only assertion: PASS")

    best = max(rows, key=lambda r: r["mod"])
    print(f"\nSELECTED {best['name']}  mod={best['mod']:.6g}  live={best['n_live']}")
    json.dump(
        {"selected": best, "scanned": rows, "readonly_ok": True},
        open(OUT / "d0_select.json", "w"),
        indent=2,
    )


if __name__ == "__main__":
    main()
