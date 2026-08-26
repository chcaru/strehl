"""Re-price the handicap at the geometry the gather ACTUALLY runs at.

boundary.py applied Catmull-Rom at FULL-RESOLUTION pixel spacing on demosaiced
luma. That is the wrong geometry and it under-prices the loss. align_cmd.rs
deinterleaves the CFA into four planes with stride 2 --

    let row = (ay + 2 * py + dy) * stride + ax + dx;
    *o = frame.data[row + 2 * px] as f32;

-- gathers each HALF-RESOLUTION plane, and writes back interleaved. So the
interpolator's taps are 2 OUTPUT pixels apart, and a structure at f cyc/px in
the render sits at 2f cyc/plane-px where the kernel is far weaker. Corroborated
by the artefact: BUILD-SHARP 20.2's warpmap geometry is 3516x2344, exactly half
of the 7032x4688 the gallery writes.

So model it where it happens. Deinterleave the real CFA, warp each plane, write
it back into rawpy's own buffer, and let rawpy demosaic. The frame arm is the
same decode without the warp, so the demosaic is common-mode and cancels, and
what is left is the gather alone -- measured, on real pixels, at the right
frequency.

cfa_site_channel(dx, dy) returns a Channel, not an offset, and with ca == None
t_site == t: there is NO chroma co-site on this path, which is what ORCH's
retraction says. This models alignment only.
"""
import argparse
import numpy as np
import rawpy
from pathlib import Path
import bestframe as B
from boundary import cr_axis, sweep_coords, shift_coords, tile_amp
from resample_price import cr_amp, dog_response

RAW = Path(r"D:\personal\macro")
GSCALE = 2e-3          # BUILD-SHARP 20.2, in PLANE units on a 3516 px plane


def warp_cfa(vis, g, plant=0.0):
    """Deinterleave, Catmull-Rom each half-res plane, reinterleave. Mirrors
    align_cmd.rs's loop exactly, including that the warp is in PLANE units."""
    out = vis.copy()
    h, w = vis.shape
    gh, gw = h // 2, w // 2
    cy = sweep_coords(gh, g) if g else np.arange(gh, dtype=np.float64)
    cx = sweep_coords(gw, g) if g else np.arange(gw, dtype=np.float64)
    if plant:
        cy = cy + plant
        cx = cx + plant
        cy = np.clip(cy, 1.0, gh - 3.0)
        cx = np.clip(cx, 1.0, gw - 3.0)
    for dy in range(2):
        for dx in range(2):
            pl = vis[dy:dy + 2 * gh:2, dx:dx + 2 * gw:2].astype(np.float32)
            pl = cr_axis(cr_axis(pl, cy, 0), cx, 1)
            out[dy:dy + 2 * gh:2, dx:dx + 2 * gw:2] = \
                np.clip(np.round(pl), 0, 65535).astype(np.uint16)
    return out


def decode_with(path, cfa):
    """Postprocess an ARW after substituting a modified CFA. Same params as
    bestframe.decode, so the two arms differ ONLY by the warp."""
    with rawpy.imread(str(path)) as r:
        if cfa is not None:
            r.raw_image_visible[:] = cfa
        a = r.postprocess(output_bps=16, no_auto_bright=True, use_camera_wb=True)
    assert a.dtype == np.uint16, f"rawpy returned {a.dtype}, NOT uint16"
    return a


def analytic():
    print("  analytic: band-integrated CR retention, taps at PLANE spacing")
    phis = (np.arange(2000) + 0.5) / 2000.0
    n = 512
    fx = (np.arange(n) + 0.5) / (2 * n)
    FX, FY = np.meshgrid(fx, fx, indexing="ij")
    FR = np.hypot(FX, FY)
    for alpha in (0.0, 2.0):
        w = np.where(FR <= 0.5, dog_response(FR, *B.FINE) ** 2 *
                     np.where(FR > 0, FR, 1e-9) ** (-alpha), 0.0)
        for label, mul in (("full-res spacing (what boundary.py did)", 1.0),
                           ("PLANE spacing (what the code does)", 2.0)):
            k = (cr_amp(np.clip(fx * mul, 0, 0.5), phis) ** 2).mean(axis=1)
            r = np.sqrt((w * np.outer(k, k)).sum() / w.sum())
            print(f"    alpha={alpha:.0f}  {label:<42} R = {r:.4f}  "
                  f"handicap {1/r:.4f}x")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--frac", type=float, default=0.5)
    a = ap.parse_args()
    analytic()
    rows = []
    for subj in a.subjects:
        fs = sorted((RAW / subj).glob("*.ARW"))
        k = int(round(a.frac * (len(fs) - 1)))
        path = fs[k]
        print(f"\n{'=' * 78}\n{subj}  frame {k} {path.name} of {len(fs)}\n{'=' * 78}",
              flush=True)
        with rawpy.imread(str(path)) as r:
            vis = r.raw_image_visible.copy()
        assert vis.dtype == np.uint16, f"raw CFA is {vis.dtype}, NOT uint16"
        print(f"  CFA {vis.shape} {vis.dtype}, planes {vis.shape[0]//2}x{vis.shape[1]//2}"
              f"  (BUILD-SHARP 20.2 warpmap geometry: 3516x2344)")

        base = B.luma(decode_with(path, None)).astype(np.float32)
        ye = B.tile_edges(base.shape[0], B.NTY); xe = B.tile_edges(base.shape[1], B.NTX)
        a0 = tile_amp(base, ye, xe, B.FINE)
        del base

        nul = tile_amp(B.luma(decode_with(path, warp_cfa(vis, 0.0))).astype(np.float32),
                       ye, xe, B.FINE) / a0
        print(f"  CONTROL NULL  identity warp through the same code: median "
              f"{np.nanmedian(nul):.9f} min {np.nanmin(nul):.9f} max {np.nanmax(nul):.9f}"
              f"  -> {'PASS' if np.allclose(nul, 1.0, rtol=0, atol=0) else 'FAIL'}")

        rG = tile_amp(B.luma(decode_with(path, warp_cfa(vis, GSCALE))).astype(np.float32),
                      ye, xe, B.FINE) / a0
        # A constant offset added to an ALREADY-uniform phase sweep leaves it
        # uniform, so plant=0.5 is nearly inert here and is NOT a potency test.
        # A second serial gather is: two Catmull-Rom passes must cost about R^2.
        rP = tile_amp(B.luma(decode_with(path, warp_cfa(warp_cfa(vis, GSCALE), GSCALE))
                             ).astype(np.float32), ye, xe, B.FINE) / a0
        med = float(np.nanmedian(rG))
        pred = med ** 2
        got = float(np.nanmedian(rP))
        print(f"  CONTROL POTENCY  a SECOND serial gather: predicted R^2 = "
              f"{pred:.4f}, measured {got:.4f}, ratio {got/pred:.4f}  -> "
              f"{'PASS' if 0.93 < got/pred < 1.07 else 'FAIL'}")
        for nm, r in (("align gather (plane geometry)", rG),
                      ("two serial gathers", rP)):
            q = np.nanpercentile(r, [5, 50, 95])
            print(f"  {nm:<34} median {q[1]:.5f}  p05 {q[0]:.4f} p95 {q[2]:.4f}")
        rows.append((subj, float(np.nanmedian(rG)), float(np.nanmedian(rP))))
        del vis

    print(f"\n{'=' * 78}\nSUMMARY -- FINE band retention through the REAL gather geometry")
    print("=" * 78)
    print(f"  {'subject':<28} {'R (align)':>10} {'handicap':>9} {'R (+plant)':>11}")
    for s, rg, rp in rows:
        print(f"  {s:<28} {rg:10.4f} {1/rg:8.4f}x {rp:11.4f}")


if __name__ == "__main__":
    main()