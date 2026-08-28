r"""V-REVIEW independent scoring of DELIVER-V6 vs ORCH-FAITHFUL.

Endpoint per PREREG-v6ca.md section 1: signed radial displacement of R vs G,
sign-symmetric, NOT a magenta counter -- a magenta counter is blind to the
opposite-sign orange/cyan artifact that over-correction produces.

Sites are chosen ONCE, from the OLD master's green channel, and applied to both
images, so every comparison is PAIRED per site. An unpaired median compares two
different populations; that defect was measured at +16.8 ppm of phantom signal
on dry-erase and -97.7 on the ruler.

Also reports the paired edge-width RATIO as the build-difference confound
check. A raw ratio needs no calibration and its null is exactly 1.000. The
sigma-equivalent version of this (vc_sharp.py) FAILED commission below ~0.5 px
and its numbers are not used.
"""
import numpy as np, sys, os, json
import vc_ca
import vc_sharp

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
NEW = r"C:\dev\strehl-out\DELIVER-V6\masters\%s.tiff"
CAP = 260


def keyed(res, key):
    return {(u[0], u[1]): res[key][i] for i, u in enumerate(res["used"])}


def score(subject, old_path=None, new_path=None):
    op = old_path or (OLD % subject)
    npth = new_path or (NEW % subject)
    if not os.path.exists(op):  return dict(subject=subject, verdict="OLD ABSENT")
    if not os.path.exists(npth): return dict(subject=subject, verdict="NEW ABSENT")
    a = vc_ca.load(op)
    b = vc_ca.load(npth)
    if a.shape != b.shape:
        return dict(subject=subject, verdict="GEOMETRY DIFFERS",
                    note="%s vs %s" % (a.shape, b.shape))
    H, W = a.shape[:2]
    centre = (H/2.0, W/2.0)
    S = vc_ca.sites(a[:, :, 1], centre)
    n_found = len(S)
    if n_found < vc_ca.MIN_SITES:
        return dict(subject=subject, verdict="UNSCORED", n_sites=n_found,
                    note="picker refused: %d sites < %d floor" % (n_found, vc_ca.MIN_SITES))
    S = S[::max(1, n_found//CAP)][:CAP]

    ra = vc_ca.measure(a, centre, S)
    rb = vc_ca.measure(b, centre, S)
    sa = vc_ca.summarise(ra); sb = vc_ca.summarise(rb)
    if sa.get("verdict") == "UNSCORED" or sb.get("verdict") == "UNSCORED":
        return dict(subject=subject, verdict="UNSCORED", n_sites=n_found,
                    note="too few sites voted")

    KA, KB = keyed(ra, "ppmR"), keyed(rb, "ppmR")
    both = sorted(set(KA) & set(KB))
    if len(both) < vc_ca.MIN_SITES:
        return dict(subject=subject, verdict="UNSCORED", n_sites=n_found,
                    note="paired overlap %d < %d" % (len(both), vc_ca.MIN_SITES))
    pa = np.array([KA[k] for k in both]); pb = np.array([KB[k] for k in both])
    d = pb - pa
    med = float(np.median(d)); mad = float(np.median(np.abs(d - med)))
    se = 1.253 * 1.4826 * mad / np.sqrt(len(d))

    BA, BB = keyed(ra, "ppmB"), keyed(rb, "ppmB")
    bboth = sorted(set(BA) & set(BB))
    db = np.array([BB[k] - BA[k] for k in bboth]) if bboth else np.array([0.0])
    medb = float(np.median(db))
    madb = float(np.median(np.abs(db - medb)))
    seb = 1.253 * 1.4826 * madb / np.sqrt(max(1, len(db)))

    # magnitude ratio, paired: median |new| / median |old| over the same sites
    mo = float(np.median(np.abs(pa))); mn = float(np.median(np.abs(pb)))
    ratio = mn / mo if mo > 0 else float("nan")

    # confound check: paired edge-width ratio (null exactly 1.000)
    wa = vc_sharp.widths(a, S, vc_sharp.w_fwhm)
    wb = vc_sharp.widths(b, S, vc_sharp.w_fwhm)
    wboth = sorted(set(wa) & set(wb))
    wr = float(np.median([wb[k]/wa[k] for k in wboth if wa[k] > 0])) if wboth else float("nan")

    return dict(subject=subject, verdict="SCORED", n_sites=n_found, n_paired=len(both),
                ppmR_old=float(np.median(pa)), ppmR_new=float(np.median(pb)),
                d_ppmR=med, d_mad=mad, d_se=se, nsigma=abs(med)/se if se > 0 else float("nan"),
                absR_old=mo, absR_new=mn, ratio=ratio,
                ppmB_old=float(np.median([BA[k] for k in bboth])) if bboth else float("nan"),
                ppmB_new=float(np.median([BB[k] for k in bboth])) if bboth else float("nan"),
                d_ppmB=medb, dB_se=seb, nsigmaB=abs(medb)/seb if seb > 0 else float("nan"),
                width_ratio=wr,
                dR_old=sa["dR"], dR_new=sb["dR"])


if __name__ == "__main__":
    subs = sys.argv[1:]
    if subs and subs[0] == "--selftest":
        # COMMISSION: identical images must give delta exactly 0 and ratio exactly 1
        s = subs[1]
        r = score(s, OLD % s, OLD % s)
        print("SELFTEST identity  subject=%s" % s)
        print("  d_ppmR      = %+.9f   want 0.000000000" % r["d_ppmR"])
        print("  ratio       =  %.9f   want 1.000000000" % r["ratio"])
        print("  width_ratio =  %.9f   want 1.000000000" % r["width_ratio"])
        ok = abs(r["d_ppmR"]) < 1e-9 and abs(r["ratio"]-1) < 1e-9 and abs(r["width_ratio"]-1) < 1e-9
        print("  %s" % ("PASSED" if ok else "*** FAILED ***"))
        sys.exit(0 if ok else 1)

    rows = []
    print("%-30s %5s %9s %9s %9s %7s %7s %8s %7s" %
          ("subject", "n", "ppmR_old", "ppmR_new", "delta", "nsig", "ratio", "d_ppmB", "widthR"))
    print("-" * 104)
    for s in subs:
        r = score(s)
        rows.append(r)
        if r["verdict"] != "SCORED":
            print("%-30s  %s  %s" % (s, r["verdict"], r.get("note", "")))
        else:
            print("%-30s %5d %+9.1f %+9.1f %+9.1f %7.1f %7.3f %+8.1f %7.4f" %
                  (s, r["n_paired"], r["ppmR_old"], r["ppmR_new"], r["d_ppmR"],
                   r["nsigma"], r["ratio"], r["d_ppmB"], r["width_ratio"]))
        sys.stdout.flush()
    with open("vc_score.json", "w") as f:
        json.dump(rows, f, indent=1)
    print("\nwrote vc_score.json  (%d rows)" % len(rows))
