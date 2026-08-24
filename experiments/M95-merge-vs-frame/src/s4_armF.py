"""S4 -- render arm F: single frames through the identical output path.

For each detail ROI we need the frame the independent focus curve says is
sharpest, its immediate neighbours (rule 4: an argmax over 299 noisy scores is
not a fact, so the neighbourhood has to be reported), and the deliberately
defocused frames the R2 power control needs.

Each is rendered by copying the one `.ARW` into its own directory and running
the SAME pinned binary with the SAME flags as the merge, `STREHL_ALIGN=0`.
Same decode, same levels, same white balance, same binning, same writer, same
crop, same grid. R4 certifies that this really is the frame.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
OFFSETS = [0, 1, -1, 2, -2, 10, -10, 25, -25]


def render(idx: int, path: str, demosaic: bool) -> dict:
    tag = f"f{idx:03d}" + ("-demo" if demosaic else "")
    d = os.path.join(L.FRAMES, tag)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, os.path.basename(path))
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
    tif = os.path.join(L.OUT, f"armF-{tag}.tif")
    if os.path.exists(tif):
        return dict(idx=idx, tif=tif, cached=True, sha=L.sha256(tif))
    args = [
        "stack",
        d,
        "-o",
        tif,
        "--gate",
        "0",
    ] + (["--demosaic"] if demosaic else [])
    t0 = time.time()
    log = L.run_strehl(args, align="0")
    with open(os.path.join(L.OUT, f"armF-{tag}.log"), "w", encoding="utf-8") as f:
        f.write(log)
    assert "alignment      : OFF" in log or "alignment" not in log, log[:2000]
    return dict(idx=idx, tif=tif, cached=False, secs=round(time.time() - t0, 1), sha=L.sha256(tif))


def main() -> int:
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))
    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    n = len(paths)

    want: dict[int, list[str]] = {}
    for nm, r in focus["res"].items():
        if nm == "ROI-FLAT":
            continue
        pk = r["peak_frame"]
        for o in OFFSETS:
            i = pk + o
            if 0 <= i < n:
                want.setdefault(i, []).append(f"{nm}{o:+d}")
    peaks = sorted({focus["res"][nm]["peak_frame"] for nm in focus["res"] if nm != "ROI-FLAT"})
    print(f"peak frames    : {peaks}")
    print(f"frames to render: {len(want)}  {sorted(want)}")

    recs = {}
    t0 = time.time()
    for k, i in enumerate(sorted(want)):
        r = render(i, paths[k * 0 + i], demosaic=False)
        r["roles"] = want[i]
        r["arw"] = os.path.basename(paths[i])
        recs[str(i)] = r
        print(
            f"  [{k+1:2d}/{len(want)}] frame {i:3d} {r['arw']}  "
            f"{'cached' if r['cached'] else str(r['secs']) + 's':>8}  sha {r['sha'][:12]}  "
            f"roles {','.join(want[i])}",
            flush=True,
        )
    print(f"binned-linear renders: {time.time()-t0:.1f}s")

    demo = {}
    for i in peaks:
        r = render(i, paths[i], demosaic=True)
        r["arw"] = os.path.basename(paths[i])
        demo[str(i)] = r
        print(f"  demosaic frame {i:3d}  {'cached' if r['cached'] else str(r['secs'])+'s'}  sha {r['sha'][:12]}")

    # R5 part 1: every render must be a DISTINCT file. Two arms that silently
    # produced the same bytes would make any comparison trivially "no loss".
    shas = [v["sha"] for v in recs.values()]
    dup = len(shas) - len(set(shas))
    print(f"\nR5 distinctness: {len(shas)} renders, {len(set(shas))} unique sha256, {dup} collisions")
    assert dup == 0, "two single-frame renders produced identical bytes"

    dst = os.path.join(OUTDIR, "s4_armF.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump({"binlin": recs, "demosaic": demo, "peaks": peaks}, f, indent=2)
    print(f"wrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
