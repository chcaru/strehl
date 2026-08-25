"""M122 — the answer to SYNTHESIS question 203.

Joins the per-stack drift (`drift-corpus.json`) to the per-stack blotch response
(`blotch-ab.json`), applies the exclusion rules fixed in PREREGISTRATION.md
section 6.4, and computes the pre-registered correlation and verdict.

The verdict is computed HERE, from the thresholds registered before any number
existed. It is not read off a table by eye.

Reads only. Writes only under C:\\dev\\strehl-out\\M122.
"""

import glob
import json
import os
import re

import numpy as np

OUT = r"C:\dev\strehl-out\M122"
LOGS = os.path.join(OUT, "logs")
RNG = np.random.default_rng(20261122)
NPERM = 20000


# ---------------------------------------------------------------- statistics
def rankdata(a):
    a = np.asarray(a, dtype=np.float64)
    order = a.argsort()
    ranks = np.empty(len(a), dtype=np.float64)
    ranks[order] = np.arange(1, len(a) + 1, dtype=np.float64)
    # average ties
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    for i in np.where(cnt > 1)[0]:
        m = inv == i
        ranks[m] = ranks[m].mean()
    return ranks


def pearson(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    x = x - x.mean()
    y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))


def perm_p(x, y, rho, nperm=NPERM):
    """Permutation null for Spearman. Returns (p_one_sided_positive, p_two_sided, null_sd)."""
    rx = rankdata(x)
    ry = rankdata(y)
    null = np.empty(nperm)
    for i in range(nperm):
        null[i] = pearson(rx, RNG.permutation(ry))
    p1 = float((np.sum(null >= rho) + 1) / (nperm + 1))
    p2 = float((np.sum(np.abs(null) >= abs(rho)) + 1) / (nperm + 1))
    return p1, p2, float(null.std())


def partial_spearman(x, y, z):
    """Spearman of x,y controlling for z."""
    rxy, rxz, ryz = spearman(x, y), spearman(x, z), spearman(y, z)
    den = np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (float((rxy - rxz * ryz) / den) if den > 0 else float("nan")), rxy, rxz, ryz


# ------------------------------------------- control 5.5: instrument self-test
def self_test():
    n = 20
    x = np.arange(n, dtype=np.float64)
    mono = x ** 2                      # perfectly monotone
    r1 = spearman(x, mono)
    p1a, _, _ = perm_p(x, mono, r1, nperm=2000)
    rr = np.random.default_rng(7).normal(size=n)
    r2 = spearman(x, rr)
    p2a, p2b, sd2 = perm_p(x, rr, r2, nperm=2000)
    ok = (abs(r1 - 1.0) < 1e-12 and p1a < 1e-3 and abs(r2) < 0.5 and p2b > 0.05)
    print("C5.5 correlation instrument self-test")
    print("   monotone pair : rho %.6f  p(one-sided) %.5f   (want 1.000000, <1e-3)" % (r1, p1a))
    print("   random pair   : rho %+.4f  p(two-sided) %.4f  null sd %.4f "
          "(want |rho|<0.5, p>0.05)" % (r2, p2b, sd2))
    print("   -> %s" % ("PASS" if ok else "FAIL -- the correlation is arithmetic, not evidence"))
    print()
    return ok


# ------------------------------------------------------------------ log scrape
def gain_spans():
    """A5: the fitted per-frame photometric gain span the binary printed, per stack."""
    out = {}
    for p in glob.glob(os.path.join(LOGS, "*__A1-photometric.log")):
        subj = os.path.basename(p).split("__")[0]
        txt = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"gain span\s+:\s+([0-9.]+)", txt)
        r = re.search(r"REFUSED\s+:\s+(\d+) frame", txt)
        k = re.search(r"region\s+:\s+(\d+) px low-detail on frame (\d+), (\d+) px after eroding", txt)
        out[subj] = {
            "gain_span": float(m.group(1)) if m else None,
            "refused": int(r.group(1)) if r else 0,
            "region_px": int(k.group(3)) if k else None,
            "exit": int(re.search(r"# exit\s+(-?\d+)", txt).group(1)),
        }
    return out


# ----------------------------------------------------------------------- main
def main():
    st_ok = self_test()

    drift = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "drift-corpus.json")))}
    blotch = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "blotch-ab.json")))}
    gs = gain_spans()

    hashes = {}
    for line in open(os.path.join(OUT, "ledger-measure.csv"), encoding="utf-8"):
        pass
    import csv
    with open(os.path.join(OUT, "ledger-measure.csv"), newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            hashes.setdefault(row["subject"], {})[row["arm"]] = (row["sha256"], row["exit"])

    used, excluded = [], []
    for s in sorted(drift):
        b = blotch.get(s)
        h = hashes.get(s, {})
        a0 = h.get("A0-default", ("", "?"))
        a1 = h.get("A1-photometric", ("", "?"))
        if a1[1] != "0" or not a1[0]:
            excluded.append((s, "E2 A1 exit %s (--photometric refused to run)" % a1[1]))
            continue
        if a0[0] and a0[0] == a1[0]:
            excluded.append((s, "E3 A0 == A1 byte-identical (plumbing null: gain span %s, %d frames refused)"
                             % (gs.get(s, {}).get("gain_span"), gs.get(s, {}).get("refused", -1))))
            continue
        if b is None or "excluded" in b:
            excluded.append((s, b.get("excluded", "no A/B row") if b else "no A/B row"))
            continue
        if not b["commissioning_ok"]:
            excluded.append((s, "E4 commissioning failed"))
            continue
        used.append(s)

    print("=" * 100)
    print("PER-STACK TABLE  (usable = %d, excluded = %d)" % (len(used), len(excluded)))
    print("=" * 100)
    hdr = ("%-38s %7s %7s %7s %7s %7s %7s %8s %8s %7s"
           % ("stack", "Dpp%", "B12", "B6", "Sdd12", "T12", "T12sep", "hf0", "dHF", "gain"))
    print(hdr)
    for s in used:
        d, b = drift[s], blotch[s]
        g = gs.get(s, {}).get("gain_span")
        print("%-38s %7.3f %7.4f %7.4f %7.4f %7.4f %7.4f %8.1f %+8.2f %7s"
              % (s, d["Dpp"], b["B12"], b["B6"], b["Sdd12"], b["T12"], b["T12sep"],
                 b["hf0_smooth_median"], b["dHF"], "%.4f" % g if g else "n/a"))
    print()
    for s, why in excluded:
        print("  EXCLUDED  %-36s %s" % (s, why))
    print()

    x = np.array([drift[s]["Dpp"] for s in used])
    y = np.array([1.0 - blotch[s]["B12"] for s in used])
    b12 = np.array([blotch[s]["B12"] for s in used])
    t12 = np.array([blotch[s]["T12"] for s in used])
    hf0 = np.array([blotch[s]["hf0_smooth_median"] for s in used])
    dhf = np.array([blotch[s]["dHF"] for s in used])
    sdd = np.array([1.0 - blotch[s]["Sdd12"] for s in used])
    dwin = np.array([drift[s]["Dwin_median"] for s in used])
    blur_t = np.array([blotch[s]["blur_plant_textured"] for s in used])

    rho = spearman(x, y)
    p1, p2, nsd = perm_p(x, y, rho)
    print("=" * 100)
    print("PRIMARY  (PREREGISTRATION section 6.1):  Spearman rho( Dpp , 1 - B12 )")
    print("=" * 100)
    print("  n = %d   rho = %+.4f   one-sided p = %.4f   two-sided p = %.4f   "
          "permutation null sd = %.4f" % (len(used), rho, p1, p2, nsd))
    print("  Pearson (reported for shape only) = %+.4f" % pearson(x, y))
    print()

    iqr_b = float(np.percentile(b12, 75) - np.percentile(b12, 25))
    iqr_d = float(np.percentile(x, 75) - np.percentile(x, 25))
    print("  POWER CHECK   IQR(B12) = %.4f  (needs >= 0.02)   IQR(Dpp) = %.3f pp  (needs >= 1.0)"
          % (iqr_b, iqr_d))
    print()

    print("ADVERSARIAL / SECONDARY (section 6.3)")
    pr, rxy, rxz, ryz = partial_spearman(x, y, hf0)
    print("  A1 floor confound : rho(Dpp, hf0(A0)) = %+.4f ; rho(1-B12, hf0) = %+.4f ;"
          % (rxz, ryz))
    print("                      PARTIAL rho(Dpp, 1-B12 | hf0) = %+.4f  (needs >= +0.20 or the"
          " headline is confounded)" % pr)
    r_a2 = spearman(x, dhf)
    pa2, _, _ = perm_p(x, dhf, r_a2, nperm=5000)
    print("  A2 absolute dHF   : rho(Dpp, dHF) = %+.4f  one-sided p = %.4f" % (r_a2, pa2))
    r_a3 = spearman(x, sdd)
    pa3, _, _ = perm_p(x, sdd, r_a3, nperm=5000)
    print("  A3 sdd statistic  : rho(Dpp, 1-Sdd12) = %+.4f  one-sided p = %.4f" % (r_a3, pa3))
    r_a4 = spearman(x, dwin)
    print("  A4 drift estimator: rho(Dpp, Dwin) = %+.4f   (agreement between the two estimators)"
          % r_a4)
    r_a4b = spearman(dwin, y)
    p4b, _, _ = perm_p(dwin, y, r_a4b, nperm=5000)
    print("                      rho(Dwin, 1-B12) = %+.4f  one-sided p = %.4f   "
          "(the estimator that argues against, discipline 829)" % (r_a4b, p4b))
    g = np.array([gs.get(s, {}).get("gain_span") or np.nan for s in used])
    ok = np.isfinite(g)
    if ok.sum() >= 6:
        r_a5 = spearman(x[ok], (g[ok] - 1.0) * 100)
        r_a5b = spearman((g[ok] - 1.0) * 100, y[ok])
        p5b, _, _ = perm_p((g[ok] - 1.0) * 100, y[ok], r_a5b, nperm=5000)
        print("  A5 fitted gain    : rho(Dpp, gain span-1) = %+.4f (n=%d) ; "
              "rho(gain span-1, 1-B12) = %+.4f  one-sided p = %.4f"
              % (r_a5, ok.sum(), r_a5b, p5b))
    print()

    print("CONTROLS")
    bad_blur = [(used[i], blur_t[i]) for i in range(len(used)) if not blur_t[i] < 0.90]
    print("  blur-control POWER plant (sigma 0.5, textured, must be < 0.90): "
          "median %.4f, worst %.4f -> %s"
          % (np.median(blur_t), blur_t.max(), "PASS" if not bad_blur else "FAIL on %s" % bad_blur))
    responders = [used[i] for i in range(len(used)) if b12[i] < 0.97]
    blurring = [(used[i], t12[i]) for i in range(len(used)) if b12[i] < 0.97 and t12[i] < 0.97]
    print("  responders (B12 < 0.97): %s" % (responders or "none"))
    print("  of those, blurring (T12 < 0.97): %s" % (blurring or "none"))
    harmed = [(used[i], b12[i]) for i in range(len(used)) if b12[i] > 1.03]
    print("  harm (B12 > 1.03): %s" % (harmed or "none"))
    lo = int(np.argmin(x))
    print("  low-drift control: lowest Dpp is %s at %.3f%% -> B12 %.4f (needs >= 0.97)"
          % (used[lo], x[lo], b12[lo]))
    print()

    # ------------------------------------------------------------- the verdict
    P1 = len(used) >= 12
    P2 = (rho >= 0.50) and (p1 < 0.05)
    P3 = not harmed
    P4 = not blurring
    P5 = b12[lo] >= 0.97
    K1 = (rho < 0.20) or (p1 >= 0.05)
    K2 = bool(harmed)
    K3 = bool(blurring)
    no_power = (iqr_b < 0.02) or (iqr_d < 1.0)

    print("PRE-REGISTERED CRITERIA (section 6.1)")
    for lab, v, txt in [("P1", P1, "n_usable >= 12"),
                        ("P2", P2, "rho >= +0.50 and one-sided p < 0.05"),
                        ("P3", P3, "no stack with B12 > 1.03"),
                        ("P4", P4, "no responder with T12 < 0.97"),
                        ("P5", P5, "lowest-drift stack has B12 >= 0.97")]:
        print("   %s %-45s %s" % (lab, txt, "PASS" if v else "FAIL"))
    for lab, v, txt in [("K1", K1, "rho < +0.20 or p >= 0.05"),
                        ("K2", K2, "any stack B12 > 1.03"),
                        ("K3", K3, "any responder T12 < 0.97")]:
        print("   %s %-45s %s" % (lab, txt, "FIRED" if v else "clear"))
    print("   power check %-41s %s" % ("IQR(B12) >= 0.02 and IQR(Dpp) >= 1.0",
                                       "FAIL - NO POWER" if no_power else "PASS"))

    if no_power:
        verdict = "INCONCLUSIVE (no power)"
    elif K1 or K2 or K3:
        verdict = "KEEP-OFF"
    elif P1 and P2 and P3 and P4 and P5:
        verdict = "PROMOTE"
    else:
        verdict = "INCONCLUSIVE"

    L1 = (abs(rho) < 0.20 and p1 >= 0.05 and bool((b12 < 0.85).any()))
    L2 = [(used[i], x[i], b12[i]) for i in range(len(used)) if x[i] < 1.5 and b12[i] < 0.85]
    print()
    print("  VERDICT: %s" % verdict)
    print("  fact 1640 broken-link test (section 6.2):")
    print("     L1 (null rho with a real responder present) : %s" % ("FIRED" if L1 else "clear"))
    print("     L2 (strong fix on a near-zero-drift stack)  : %s" % (L2 if L2 else "clear"))
    print()

    json.dump({
        "used": used, "excluded": excluded, "self_test_ok": bool(st_ok),
        "rho": rho, "p_one": p1, "p_two": p2, "null_sd": nsd, "n": len(used),
        "iqr_B12": iqr_b, "iqr_Dpp": iqr_d,
        "partial_rho": pr, "rho_Dpp_hf0": rxz, "rho_y_hf0": ryz,
        "rho_dHF": r_a2, "rho_sdd": r_a3, "rho_Dwin_Dpp": r_a4, "rho_Dwin_y": r_a4b,
        "responders": responders, "blurring": blurring, "harmed": harmed,
        "lowest_drift_stack": used[lo], "lowest_drift": float(x[lo]),
        "lowest_drift_B12": float(b12[lo]),
        "verdict": verdict, "L1": bool(L1), "L2": L2,
        "criteria": {"P1": bool(P1), "P2": bool(P2), "P3": bool(P3), "P4": bool(P4),
                     "P5": bool(P5), "K1": bool(K1), "K2": bool(K2), "K3": bool(K3),
                     "no_power": bool(no_power)},
        "gain_spans": gs,
    }, open(os.path.join(OUT, "correlate.json"), "w"), indent=1)
    print("wrote %s" % os.path.join(OUT, "correlate.json"))


if __name__ == "__main__":
    main()
