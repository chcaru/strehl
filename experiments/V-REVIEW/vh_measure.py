"""Measure edge overshoot at full resolution and after the gallery reduction,
on the SAME edges, with V-REVIEW's own instrument.

  python vh_measure.py <subject> [nsites]

Sites are found in the MASTER, then mapped into each reduced image by dividing
by the scale and re-localising the edge within +-3 px along its own normal (the
reduction moves the edge by up to half a reduced pixel; not re-localising would
measure the shoulder of a shifted edge and invent a rim).

Windows are matched in PHYSICAL extent: R = 80 master px = 16 reduced px, and
the shoulder/reference zones are expressed in units of the edge's own width, so
the two scales are measured the same way.

ARMS
  full          the master itself
  box           PIL BOX      (area average -- NO negative lobes)
  bilinear      PIL BILINEAR (NO negative lobes)
  bicubic       PIL BICUBIC  (negative lobes)
  lanczos       PIL LANCZOS  (negative lobes)  <- what viewable.py actually uses
  gallery       the ACTUAL delivered chain: 16->8 bit, LANCZOS to 1400, JPEG q95

Reducing the luminance plane and reducing RGB then taking luminance are the same
operation, because PIL's mode-'F' resize is linear and luminance is a linear
combination of the channels.  The `gallery` arm is not linear (8-bit rounding,
JPEG) and is therefore run on RGB, as delivered.
"""
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_lib as H

R_FULL, TAN_FULL = 80.0, 40.0
KERNELS = ("box", "bilinear", "bicubic", "lanczos")


def find_sites(lm, want, cells=(28, 42)):
    g = cv2.GaussianBlur(lm, (0, 0), 2.0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5)
    mag = cv2.magnitude(gx, gy)
    h, w = lm.shape
    ch, cw = h // cells[0], w // cells[1]
    cand = []
    for iy in range(cells[0]):
        for ix in range(cells[1]):
            y0, x0 = iy * ch, ix * cw
            blk = mag[y0:y0 + ch, x0:x0 + cw]
            j = int(np.argmax(blk)); yy, xx = divmod(j, blk.shape[1])
            cand.append((float(blk[yy, xx]), y0 + yy, x0 + xx))
    cand.sort(reverse=True)

    out = []
    for _, y, x in cand:
        if y < 150 or x < 150 or y > h - 150 or x > w - 150:
            continue
        nx, ny = float(gx[y, x]), float(gy[y, x])
        n = np.hypot(nx, ny)
        if n < 1e-6:
            continue
        nx, ny = nx / n, ny / n
        # straightness: gradient orientation must be consistent along the tangent
        tx, ty = -ny, nx
        ss = np.arange(-25, 26, 5.0)
        ang = np.arctan2(H.bilinear(gy, y + ss * ty, x + ss * tx),
                         H.bilinear(gx, y + ss * ty, x + ss * tx))
        cs, sn = np.cos(ang).mean(), np.sin(ang).mean()
        if np.sqrt(-2.0 * np.log(max(np.hypot(cs, sn), 1e-9))) > H.ORIENT_TOL:
            continue
        us, p = H.profile_at(lm, y, x, nx, ny, R_FULL, TAN_FULL)
        if p[-1] < p[0]:                 # orient dark -> bright
            nx, ny = -nx, -ny
            us, p = H.profile_at(lm, y, x, nx, ny, R_FULL, TAN_FULL)
        r = H.analyse(us, p)
        if r is None:
            continue
        r.update(y=int(y), x=int(x), nx=nx, ny=ny)
        out.append(r)
        if len(out) >= want:
            break
    return out


def relocalise(plane, y, x, nx, ny, span=3.0):
    """The reduction shifts the edge by up to half a reduced pixel."""
    us = np.arange(-span, span + 0.25, 0.25, dtype=np.float32)
    v = H.bilinear(plane, y + us * ny, x + us * nx)
    d = np.abs(np.gradient(v))
    k = int(np.argmax(d))
    return float(y + us[k] * ny), float(x + us[k] * nx)


def measure_reduced(plane, sc, sites, R, tan):
    rows = []
    for s in sites:
        y, x = s["y"] / sc, s["x"] / sc
        y, x = relocalise(plane, y, x, s["nx"], s["ny"])
        us, p = H.profile_at(plane, y, x, s["nx"], s["ny"], R, tan)
        r = H.analyse(us, p)
        rows.append(r)
    return rows


def main():
    subject = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    rgb = H.read_master(subject)
    lm = H.lum(rgb).astype(np.float32)
    sites = find_sites(lm, want)
    print("SUBJECT %s   master %dx%d   accepted sites %d"
          % (subject, lm.shape[1], lm.shape[0], len(sites)))
    if not sites:
        print("no site met the declared floors -- NOT EXAMINED"); return 1

    sc = lm.shape[1] / float(H.GALLERY_MAXW)
    R_RED, TAN_RED = R_FULL / sc, max(4.0, round(TAN_FULL / sc))
    print("scale %.4fx   R_full %.0f px = %.1f reduced px   tangent %.0f / %.0f"
          % (sc, R_FULL, R_RED, TAN_FULL, TAN_RED))

    arms = {"full": [dict(s) for s in sites]}
    for kern in KERNELS:
        red, _ = H.reduce_plane(lm, kernel=kern)
        arms[kern] = measure_reduced(red, sc, sites, R_RED, TAN_RED)
    grgb, _ = H.gallery_chain(rgb.astype(np.uint16))
    arms["gallery"] = measure_reduced(H.lum(grgb).astype(np.float32), sc, sites,
                                      R_RED, TAN_RED)

    print("")
    print("%-10s %5s %9s %9s %9s %9s %8s %8s"
          % ("arm", "n", "over_med", "over_mean", "excess", "pct_med", "rings", "floor"))
    summ = {}
    for name in ("full",) + KERNELS + ("gallery",):
        rows = [r for r in arms[name] if r is not None]
        if not rows:
            print("%-10s %5d   all sites rejected" % (name, 0)); continue
        ov = np.array([r["overshoot_dn"] for r in rows])
        ex = np.array([r["over_excess"] for r in rows])
        pc = np.array([r["overshoot_pct"] for r in rows])
        rg = np.mean([r["rings"] for r in rows])
        fl = np.median([r["null_mean"] for r in rows])
        summ[name] = dict(n=len(rows), over_med=float(np.median(ov)),
                          over_mean=float(ov.mean()), excess_med=float(np.median(ex)),
                          pct_med=float(np.median(pc)), rings=float(rg), floor=float(fl))
        print("%-10s %5d %9.2f %9.2f %9.2f %8.2f%% %7.0f%% %8.2f"
              % (name, len(rows), np.median(ov), ov.mean(), np.median(ex),
                 np.median(pc), 100 * rg, fl))

    # paired, on the sites that survive in BOTH arms
    print("")
    print("PAIRED vs full resolution (same site, same edge):")
    for name in KERNELS + ("gallery",):
        pair = [(a, b) for a, b in zip(arms["full"], arms[name])
                if a is not None and b is not None]
        if not pair:
            continue
        d = np.array([b["overshoot_dn"] - a["overshoot_dn"] for a, b in pair])
        de = np.array([b["over_excess"] - a["over_excess"] for a, b in pair])
        flips = sum(1 for a, b in pair
                    if a["overshoot_dn"] <= a["null_mean"] and b["rings"])
        print("  %-9s n=%3d  d_overshoot med %+8.2f  d_excess med %+8.2f  "
              "clean->ringing %d/%d" % (name, len(pair), np.median(d), np.median(de),
                                        flips, len(pair)))

    os.makedirs(H.OUT, exist_ok=True)
    with open(os.path.join(H.OUT, "halo_%s.json" % subject), "w") as fh:
        json.dump(dict(subject=subject, scale=sc, n_sites=len(sites),
                       summary=summ,
                       arms={k: [r for r in v] for k, v in arms.items()}), fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
