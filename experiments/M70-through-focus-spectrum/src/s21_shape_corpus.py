"""M70 s21 - the corpus read against PREREGISTRATION-C's bars.

Where does the real through-focus shape depart from a Gaussian?

Statistic R10_50 = w(0.10)/w(0.50), Gaussian = 1.822616, bar +/-0.11.
Criteria H / I / J, VOID 11-14. Read once, reported as it falls.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s14_asym_controls as S14  # noqa: E402
import s16_null_band as S16  # noqa: E402
import s20_shape_controls as S20  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
G = S20.GAUSS["R10_50"]
G25 = S20.GAUSS["R25_50"]
BAR = 0.11
PHYS = 1.766
POWERED = {"foam", "coffee-bean", "wrapped-text-2", "wrapped-text-1",
           "bee-1", "bee-2", "bee-3"}
# Section 16.5 per-stack shuffle null sd on A50, for the pairing discussion.
A50_Z = {"coffee-bubbles": 1.4, "109MSDCF": 0.1, "119MSDCF": 0.8, "113MSDCF": 1.1,
         "112MSDCF": 1.6, "foam": 89.1, "coffee-bean": 39.2, "wrapped-text-2": 35.5,
         "wrapped-text-1": 125.7, "bee-1": 19.6, "bee-2": 12.7, "bee-3": 32.2}


def ratios(curve):
    o = S20.widths(curve)
    return o["R10_50"], o["R25_50"], o["w50"], (o["w10_cens"] or o["w50_cens"])


def stack_curves(stack, sigma_scale=1.0):
    d = A5.load(stack)
    s, nvar = A5.signal(d, sigma_scale)
    tex, _ = A5.classify(d, s, nvar)
    out = []
    for p in np.where(tex)[0]:
        for bname in M.MID_BANDS:
            out.append(s[:, p, d["bands"].index(bname)].astype(np.float64))
    return out, s.shape[0]


def read(cs, mode="intact", rng=None):
    r10, r25, w50, nund, ncens = [], [], [], 0, 0
    for c in cs:
        x = c
        if mode == "reversed":
            x = c[::-1]
        elif mode == "shuffle":
            x = rng.permutation(c)
        a, b, w, cens = ratios(x)
        if np.isfinite(a):
            r10.append(a)
            w50.append(w)
            if cens:
                ncens += 1
        else:
            nund += 1
        if np.isfinite(b):
            r25.append(b)
    return {"R10_50": np.array(r10), "R25_50": np.array(r25),
            "w50": np.array(w50), "undef": nund, "cens": ncens, "n": len(cs)}


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    res = {"gauss": G, "bar": BAR, "phys": PHYS, "stacks": {}}
    rng = np.random.default_rng(70)

    hdr("CORPUS - R10_50 per stack   (Gaussian 1.8226, physical defocus plant 1.766, bar +/-0.11)")
    print(f"{'stack':<16}{'K':>5}{'n':>7}{'undef%':>8}{'cens%':>7}{'w50':>8}"
          f"{'R25/50':>9}{'R10/50':>9}{'vs G':>8}{'vs phys':>9}{'pwr':>5}")
    rowsH = []
    for st in S16.STACKS:
        cs, K = stack_curves(st)
        r = read(cs)
        if r["R10_50"].size == 0:
            print(f"{st:<16}{K:>5}{r['n']:>7}  ALL UNDEFINED")
            continue
        m10 = float(np.median(r["R10_50"]))
        m25 = float(np.median(r["R25_50"])) if r["R25_50"].size else float("nan")
        e = {"K": K, "n": r["n"], "undef": r["undef"] / max(1, r["n"]),
             "cens": r["cens"] / max(1, r["R10_50"].size),
             "w50": float(np.median(r["w50"])), "R25_50": m25, "R10_50": m10,
             "powered_A50": st in POWERED}
        res["stacks"][st] = e
        rowsH.append((st, m10, e["undef"], st in POWERED))
        print(f"{st:<16}{K:>5}{r['n']:>7}{100 * e['undef']:>7.1f}%{100 * e['cens']:>6.1f}%"
              f"{e['w50']:>8.2f}{m25:>9.4f}{m10:>9.4f}{m10 - G:>+8.4f}{m10 - PHYS:>+9.4f}"
              f"{('YES' if st in POWERED else '-'):>5}")

    pw = [m for s_, m, _u, p in rowsH if p]
    al = [m for _s, m, _u, _p in rowsH]
    med_pw, med_all = float(np.median(pw)), float(np.median(al))
    res["median_powered"] = med_pw
    res["median_all"] = med_all
    print(f"\n  median over 7 POWERED stacks : {med_pw:.4f}   "
          f"({med_pw - G:+.4f} vs Gaussian, {med_pw - PHYS:+.4f} vs physical plant)")
    print(f"  median over all 12           : {med_all:.4f}   ({med_all - G:+.4f} vs Gaussian)")

    hdr("PRE-REGISTERED CRITERIA H / I / J   (bar +/-0.11, need 6 of 7 powered)")
    inH = sum(1 for s_, m, _u, p in rowsH if p and abs(m - G) <= BAR)
    inI = sum(1 for s_, m, _u, p in rowsH if p and m >= G + BAR)
    inJ = sum(1 for s_, m, _u, p in rowsH if p and m <= G - BAR)
    H = abs(med_pw - G) <= BAR and inH >= 6
    I_ = med_pw >= G + BAR and inI >= 6
    J = med_pw <= G - BAR and inJ >= 6
    print(f"  H GAUSSIAN-TO-RESOLUTION  |median-1.8226| = {abs(med_pw - G):.4f} <= 0.11 ? "
          f"{'PASS' if abs(med_pw - G) <= BAR else 'FAIL'}   "
          f"stacks within band {inH}/7 >= 6 ? {'PASS' if inH >= 6 else 'FAIL'}   => "
          f"{'MET' if H else 'NOT MET'}")
    print(f"  I HEAVIER (fact 274 dir)  median >= 1.9326 ? "
          f"{'PASS' if med_pw >= G + BAR else 'FAIL'}   stacks {inI}/7 => "
          f"{'MET' if I_ else 'NOT MET'}")
    print(f"  J LIGHTER                 median <= 1.7126 ? "
          f"{'PASS' if med_pw <= G - BAR else 'FAIL'}   stacks {inJ}/7 => "
          f"{'MET' if J else 'NOT MET'}")
    res["criteria"] = {"H": bool(H), "I": bool(I_), "J": bool(J),
                       "inH": inH, "inI": inI, "inJ": inJ}
    verdict = "H GAUSSIAN" if H else ("I HEAVIER" if I_ else ("J LIGHTER" if J else "INDETERMINATE"))
    print(f"\n  VERDICT: {verdict}")
    res["verdict"] = verdict

    hdr("VOID 11 - censoring / undefined rate")
    bad = [s_ for s_, _m, u, p in rowsH if p and u > 0.50]
    print(f"  powered stacks with >50% undefined: {len(bad)}/7  {bad}")
    print(f"  VOID 11 {'FIRES' if len(bad) >= 4 else 'does not fire'}")
    res["void11"] = len(bad) >= 4

    hdr("VOID 13 - reversal must be EXACT (R10_50 is near/far symmetric by construction)")
    worst = 0.0
    for st in S16.STACKS[:4]:
        cs, _K = stack_curves(st)
        a = read(cs)["R10_50"]
        b = read(cs, "reversed")["R10_50"]
        n = min(a.size, b.size)
        d = float(np.max(np.abs(np.median(a) - np.median(b)))) if n else 0.0
        worst = max(worst, d)
        print(f"  {st:<16} intact {np.median(a):.6f}   reversed {np.median(b):.6f}   "
              f"delta {d:.9f}")
    print(f"  VOID 13 {'FIRES' if worst > 1e-12 else 'does not fire'}  (worst {worst:.2e})")
    res["void13"] = {"worst": worst, "fires": bool(worst > 1e-12)}

    hdr("VOID 12 - per-stack shuffle null (does R10_50 read the CURVE?)  40 reps")
    print(f"{'stack':<16}{'intact':>9}{'shuffle med':>13}{'shuffle sd':>12}"
          f"{'|gap|':>8}{'z':>8}{'powered?':>10}")
    res["null"] = {}
    for st in S16.STACKS:
        cs, _K = stack_curves(st)
        it = float(np.median(read(cs)["R10_50"]))
        sh = []
        for rep in range(40):
            r = read(cs, "shuffle", np.random.default_rng(9000 + rep))["R10_50"]
            if r.size:
                sh.append(float(np.median(r)))
        sh = np.array(sh)
        sd = float(sh.std(ddof=1)) if sh.size > 1 else float("nan")
        gap = abs(it - float(np.median(sh))) if sh.size else float("nan")
        z = gap / sd if sd and np.isfinite(sd) and sd > 0 else float("inf")
        res["null"][st] = {"intact": it, "shuffle_med": float(np.median(sh)),
                           "shuffle_sd": sd, "gap": gap, "z": z}
        print(f"{st:<16}{it:>9.4f}{np.median(sh):>13.4f}{sd:>12.4f}{gap:>8.4f}"
              f"{z:>8.1f}{('YES' if z >= 3 else 'NO'):>10}")
    close = [s_ for s_ in res["null"] if s_ in POWERED and res["null"][s_]["gap"] <= BAR]
    print(f"\n  powered stacks whose shuffle null is within 0.11 of intact: "
          f"{len(close)}/7  {close}")
    print(f"  VOID 12 {'FIRES' if len(close) >= 4 else 'does not fire'}")
    res["void12"] = len(close) >= 4

    hdr("VOID 14 - sigma sweep (FOCUS_NOISE_SD is unsettled; M69 is live on it)")
    print(f"{'sigma x':>9}{'median powered R10_50':>24}{'vs 1.0x':>10}")
    res["sigma"] = {}
    base = None
    for sc in (0.91, 1.00, 1.09, 1.25):
        ms = []
        for st in S16.STACKS:
            if st not in POWERED:
                continue
            cs, _K = stack_curves(st, sigma_scale=sc)
            r = read(cs)["R10_50"]
            if r.size:
                ms.append(float(np.median(r)))
        m = float(np.median(ms))
        if base is None:
            base = m
        res["sigma"][f"x{sc}"] = m
        print(f"{sc:>9.2f}{m:>24.4f}{m - base:>+10.4f}")
    sv = list(res["sigma"].values())
    span = max(sv) - min(sv)
    print(f"\n  span {span:.4f}  VOID 14 {'FIRES' if span > BAR else 'does not fire'}")
    res["void14"] = {"span": span, "fires": bool(span > BAR)}

    hdr("CONFOUND - can scene geometry alone move R10_50? (two-depth, symmetric PSF)")
    print("  M25 question 33 made concrete: the PSF here is symmetric by construction,")
    print("  so anything R10_50 reads is scene geometry, not optics.")
    print(f"{'sep':>6}{'w_far':>8}{'R10_50':>10}{'vs G':>9}{'n':>6}")
    res["confound"] = []
    import s03_plant as P3
    lat, _ = P3.load_latent()
    crng = np.random.default_rng(4242)
    for sep, wf in ((3, 0.30), (6, 0.30), (6, 0.15), (10, 0.30), (10, 0.15)):
        cs = []
        for _ in range(8):
            r0, r1, w = S14.two_depth(41, 0.5, sep, wf)
            f0 = P3.make_frames(lat, r0, P3.LATENT_ISO, crng, noise=False)
            f1 = P3.make_frames(lat, r1, P3.LATENT_ISO, crng, noise=False)
            mix = [(1 - w) * a + w * b for a, b in zip(f0, f1)]
            m = P3.measure_frames(mix, P3.LATENT_ISO, subtract_noise=False)
            for b in M.MID_BANDS:
                cs.append(np.array([row[b] for row in m], dtype=np.float64))
        r = read(cs)["R10_50"]
        if r.size:
            mm = float(np.median(r))
            res["confound"].append({"sep": sep, "w_far": wf, "R10_50": mm, "n": int(r.size)})
            print(f"{sep:>6}{wf:>8.2f}{mm:>10.4f}{mm - G:>+9.4f}{r.size:>6}")
    if res["confound"]:
        cm = max(abs(c["R10_50"] - G) for c in res["confound"])
        msg = ("CONFOUND CAN REACH THE BAR - readings near it are not attributable to optics"
               if cm >= BAR else "confound stays inside the bar")
        print(f"\n  max |confound - Gaussian| = {cm:.4f}   bar = {BAR}")
        print(f"  {msg}")
        res["confound_max"] = cm

    hdr("M67 INSTRUCTION (b) - the named pairing, 109MSDCF vs coffee-bean")
    for st in ("109MSDCF", "coffee-bean"):
        e = res["stacks"].get(st, {})
        n = res["null"].get(st, {})
        print(f"  {st:<14} K={e.get('K')}  R10_50={e.get('R10_50', float('nan')):.4f}  "
              f"shuffle sd={n.get('shuffle_sd', float('nan')):.4f}  "
              f"z={n.get('z', float('nan')):.1f}  "
              f"undef={100 * e.get('undef', 0):.1f}%  "
              f"[A50 z from 16.5 = {A50_Z[st]}]")

    with open(os.path.join(OUT, "s21_shape_corpus.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s21_shape_corpus.json")


if __name__ == "__main__":
    main()
