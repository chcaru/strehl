"""V-RIM batch profiler.

Adds the thing the n=2 design cannot have: a WITHIN-SUBJECT test of C2.

C2 says the ring appears only where the silhouette carries a fine fringe. Across
subjects that is confounded by scene, exposure, frame count and magnification.
Within one image it is not. So each backdrop pixel is attributed to its nearest
boundary point, that boundary point is scored for local fringe density, and the
backdrop is profiled separately behind the smoothest and the most fringed thirds
of the SAME silhouette.

fringe index = boundary length inside a disc of radius R, divided by 2R. A
straight edge scores 1. A fringe scores higher. It is measured from the mask
alone and never from the luminance being tested.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import EDGES, load_lum, otsu, profile, prominence, segment

R_FRINGE = 20


def fringe_map(subject):
    er = ndimage.binary_erosion(subject, iterations=1, border_value=1)
    bnd = (subject & ~er).astype(np.float32)
    dens = ndimage.uniform_filter(bnd, size=2 * R_FRINGE + 1, mode="nearest")
    # count of boundary px in the box, divided by the box side => length/side
    cnt = dens * (2 * R_FRINGE + 1) ** 2
    return cnt / (2.0 * R_FRINGE + 1.0), bnd.astype(bool)


def place_disc(subject, backdrop):
    """Synthetic silhouette in empty backdrop. Must clear the real subject AND
    the frame border, or the distance transform hands back an image corner."""
    h, w = subject.shape
    inner = np.zeros_like(backdrop)
    pad = 60
    inner[pad:h - pad, pad:w - pad] = True
    room = ndimage.distance_transform_edt(backdrop & inner)
    idx = int(np.argmax(room))
    cy, cx = np.unravel_index(idx, room.shape)
    rmax = float(room[cy, cx])
    if rmax < 350:
        return None, dict(room=rmax)
    r = 120.0
    yy, xx = np.ogrid[:h, :w]
    disc = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return disc, dict(cy=int(cy), cx=int(cx), radius=r, room=rmax)


def run(src, label, outdir, channel="G"):
    shape, lum = load_lum(src, channel)
    subject, backdrop, diag = segment(lum)
    print(f"== {label}  {shape} ch={channel}")
    for k, v in diag.items():
        print(f"   seg.{k:26s} {v}")

    d_out, inds = ndimage.distance_transform_edt(~subject, return_indices=True)
    d_out = d_out.astype(np.float32)
    d_in = ndimage.distance_transform_edt(subject).astype(np.float32)
    signed = d_out - d_in
    del d_in

    fmap, bnd = fringe_map(subject)
    near_f = fmap[inds[0], inds[1]]      # fringe score of the nearest boundary pt
    del inds, fmap

    m_ref = backdrop & (signed > 600) & (signed < 1400)
    if int(m_ref.sum()) < 5000:
        m_ref = backdrop & (signed > 0.6 * float(signed[backdrop].max()))
    ref = float(np.median(lum[m_ref]))
    deep = subject & (signed < -100)
    if int(deep.sum()) < 2000:
        deep = subject & (signed < -20)
    subj = float(np.median(lum[deep])) if int(deep.sum()) > 500 else float("nan")

    print(f"   far-field ref            {ref:10.1f}  over {int(m_ref.sum())} px")
    print(f"   subject interior         {subj:10.1f}")
    print(f"   contrast (ref - subject) {ref - subj:10.1f}")

    rows = profile(lum, signed, backdrop)
    print("   ALL-PERIMETER PROFILE")
    print("     d_lo  d_hi        n        med    vs ref     frac")
    for r in rows:
        print(f"    {r['lo']:5d} {r['hi']:5d} {r['n']:9d} {r['med']:10.1f} "
              f"{r['med']-ref:+9.1f} {(r['med']-ref)/ref*100:+7.2f}%")

    # ---- within-subject split by local fringe density -----------------------
    bf = near_f[backdrop & (signed > 0) & (signed < 300)]
    lo_t, hi_t = np.percentile(bf, [33.3, 66.7])
    print(f"   fringe index terciles: <= {lo_t:.3f} smooth, >= {hi_t:.3f} fringed"
          f"  (median {np.median(bf):.3f}, max {bf.max():.3f})")
    groups = {}
    for name, sel in (("smooth", near_f <= lo_t), ("fringed", near_f >= hi_t)):
        gv = backdrop & sel
        gr = profile(lum, signed, gv, minpix=150)
        if not gr:
            continue
        gref_m = gv & (signed > 600) & (signed < 1400)
        gref = float(np.median(lum[gref_m])) if int(gref_m.sum()) > 2000 else ref
        p = prominence(gr, gref, 0, 200)
        groups[name] = dict(ref=gref, edge=gr[0]["med"], rows=gr, prom=p)
        print(f"   {name.upper()} third of the perimeter, ref={gref:.1f}")
        print("     d_lo  d_hi        n        med    vs ref     frac")
        for r in gr:
            if r["lo"] > 300:
                continue
            print(f"    {r['lo']:5d} {r['hi']:5d} {r['n']:9d} {r['med']:10.1f} "
                  f"{r['med']-gref:+9.1f} {(r['med']-gref)/gref*100:+7.2f}%")
        print(f"     -> ring: {p}")

    pr_near = prominence(rows, ref, 0, 200)
    pr_all = prominence(rows, ref, 0, 1e9)
    null = prominence([r for r in rows if 600 <= r["d"] <= 2500], ref)

    # ---- placebo ------------------------------------------------------------
    placebo = None
    disc, dinfo = place_disc(subject, backdrop)
    if disc is not None:
        sd = (ndimage.distance_transform_edt(~disc)
              - ndimage.distance_transform_edt(disc)).astype(np.float32)
        pv = backdrop & ~subject & (sd > 0) & (signed > 300)
        prows = profile(lum, sd, pv, minpix=100)
        prows = [r for r in prows if r["hi"] <= 300]
        if len(prows) > 10:
            pref = float(np.median([r["med"] for r in prows[-8:]]))
            pp = prominence(prows, pref, 0, 200)
            pedge = prows[0]["med"]
            placebo = dict(info=dinfo, ref=pref, edge=pedge,
                           edge_frac=(pedge - pref) / pref, prom=pp)
            print(f"   PLACEBO disc r={dinfo['radius']:.0f} at "
                  f"({dinfo['cx']},{dinfo['cy']}) room={dinfo['room']:.0f}, "
                  f"ref={pref:.1f}")
            print("     d_lo  d_hi        n        med    vs ref     frac")
            for r in prows:
                print(f"    {r['lo']:5d} {r['hi']:5d} {r['n']:9d} {r['med']:10.1f} "
                      f"{r['med']-pref:+9.1f} {(r['med']-pref)/pref*100:+7.2f}%")
            print(f"     -> placebo edge {(pedge-pref)/pref*100:+.2f}%, ring {pp}")
    else:
        print(f"   PLACEBO skipped, clearance only {dinfo.get('room', 0):.0f} px")

    edge = rows[0]["med"]
    out = dict(label=label, file=str(src), channel=channel, shape=list(shape),
               seg=diag, ref=ref, subj=subj, edge=edge,
               edge_frac_ref=(edge - ref) / ref,
               edge_frac_contrast=(edge - ref) / (ref - subj) if ref != subj else None,
               edge_density=float(np.log10(ref / max(edge, 1e-6))),
               rows=rows, prom_near=pr_near, prom_all=pr_all, null=null,
               groups={k: dict(ref=v["ref"], edge=v["edge"], prom=v["prom"],
                               rows=v["rows"]) for k, v in groups.items()},
               fringe_terciles=[float(lo_t), float(hi_t)],
               placebo=placebo)
    print()
    print(f"   SUMMARY {label}")
    print(f"     darkening   {(edge-ref)/ref*100:+7.2f}% of far field | "
          f"{(edge-ref)/(ref-subj)*100:+7.2f}% of contrast | "
          f"{np.log10(ref/max(edge,1e-6)):+.4f} dex | {edge-ref:+.0f} DN")
    print(f"     ring<=200   {pr_near}")
    print(f"     null        {null}")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    Path(outdir, f"{label}.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2], sys.argv[3],
        sys.argv[4] if len(sys.argv) > 4 else "G")
