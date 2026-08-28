"""Emit section 9.25's tables and values from the records.

WHY THIS EXISTS. Section 9.23.12's instrument defect #11 was two table rows
transcribed into the report that had never been read out of a run. The fix is
not to type numbers at all. Every cell below is printed from JSON, and
`vn_verify25.py` re-derives the same cells from the same JSON, so the report,
the generator and the checker all trace to one record.

Records consumed:

  subgate.json         per-subject band table (`vn_subgate.py`)
  subgate-ladder.json  nested-subset N ladder, both half-splits
  rogue.json           dense ladder, weight concentration, frame 46's
                       properties, share under both weighting laws
  rogue46.json         image-space difference between merging with and
                       without frame 46 (`vn_rogue_img.py`)
"""
import io
import json
import os

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
SUBJ = ("coffee-bubbles", "112MSDCF", "bee-2-cpl@registered")


def load(name):
    with io.open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def band_of(rows, k):
    for x in rows:
        if x["band"] == k:
            return x
    return None


def t_s2(c):
    """The known-answer sweep. `r predicted` is the closed form
    `sig/(sig + (1-sig)/(n/2))`, not a fitted value."""
    out = ["| planted signal fraction | r predicted | r measured | bands "
           "scored + skipped | sub-gate fraction |",
           "|---|---:|---:|---|---:|"]
    for s in c["S2_sweep"]:
        out.append("| %.2f | %.4f | %.4f | %d + %d = %d | %.4f |"
                   % (s["sig_frac"], s["r_pred"], s["r_med"], s["n_scored"],
                      s["n_skipped"], s["n_bands"], s["dead_frac_med"]))
    return out


def t_s4(c):
    out = ["| planted signal fraction | r_mean (plain mean) | r_merge "
           "(shipping) | sel_cost |", "|---|---:|---:|---:|"]
    for s in c["S4_selection_cost"]["sweep"]:
        out.append("| %.2f | %.4f | %.4f | %+.4f |"
                   % (s["sig_frac"], s["r_mean_med"], s["r_merge_med"],
                      s["sel_cost_med"]))
    return out


def t_subgate(d):
    out = ["| subject | N | band | sub-gate fraction | sub-gate pixels | "
           "**r_subgate** | r_merge | r_mean |", "|---|---:|---|---:|---:|"
           "---:|---:|---:|"]
    for key in SUBJ:
        s = d["subjects"][key]
        x = band_of(s["rows"], 0)
        out.append("| `%s` | %d | L0 | %.4f | %d | **%.4f** | %.4f | %.4f |"
                   % (key, s["n"], x["dead_frac"], x["px_dead"],
                      x["r_subgate"], x["r_merge"], x["r_mean"]))
    return out


def t_ladder(d):
    out = ["| subject | N | L2 | L3 | L4 | L5 | L6 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for key in SUBJ:
        s = d["subjects"][key]
        for r in s["rungs"]:
            out.append("| `%s` | %d | %s |"
                       % (key, r["n"],
                          " | ".join("%+.3f" % band_of(r["rows"], k)
                                     ["sel_cost"] for k in (2, 3, 4, 5, 6))))
    return out


def t_dense(g):
    out = ["| N | frame 46 in subsample | L3 | L4 | L5 | L6 |",
           "|---:|---|---:|---:|---:|---:|"]
    for r in g["dense"]:
        out.append("| %d | %s | %s |"
                   % (r["n"], "yes" if r["rogue_present"] else "**no**",
                      " | ".join("%+.4f" % r["sel_cost"][str(k)]
                                 for k in (3, 4, 5, 6))))
    return out


def t_conc(g):
    out = ["| N | frame 46 present | half A top frame | A share | A n_eff | "
           "half B top frame | B share | B n_eff |",
           "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for r in g["conc"]:
        out.append("| %d | %s | %d | %.4f | %.2f | %d | %.4f | %.2f |"
                   % (r["n"], "yes" if r["rogue_present"] else "**no**",
                      r["A_top"], r["A_share"], r["A_neff"], r["B_top"],
                      r["B_share"], r["B_neff"]))
    return out


def t_f46(g):
    f = g["f46"]
    out = ["| quantity | frame 46 | stack median | ratio |",
           "|---|---:|---:|---:|",
           "| mean level, DN | %.1f | %.1f | **%.3fx** |"
           % (f["mean_dn"], f["stack_median_mean_dn"], f["mean_dn_ratio"]),
           "| per-frame std, DN | %.1f | %.1f | %.3fx |"
           % (f["std_dn"], f["stack_median_std_dn"], f["std_dn_ratio"])]
    for b in f["bands"]:
        if b["band"] in (0, 4, 5, 6):
            out.append("| L%d band energy | %.4g | %.4g | **%.1fx** "
                       "(rank %d of %d) |"
                       % (b["band"], b["rogue_energy"], b["median_energy"],
                          b["ratio"], b["rank"], g["n"]))
    return out


def t_rogue(g):
    n = g["n"]
    out = ["| band | shipping | rmax theta=0.25 | rmax theta=0.50 | "
           "rmax theta=0.75 | shipping vs 1/N | rmax0.75 vs 1/N |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for r in g["rogue"]:
        out.append("| L%d | %.5f | %.5f | %.5f | %.5f | %.0fx | %.0fx |"
                   % (r["band"], r["shipping"], r["rmax0.25"], r["rmax0.50"],
                      r["rmax0.75"], r["shipping"] * n, r["rmax0.75"] * n))
    return out


def t_img(m):
    out = ["| quantity | value |", "|---|---:|",
           "| RMS difference, DN | %.1f |" % m["rms_diff_dn"],
           "| as a fraction of mean level | %.4f |"
           % (m["rms_diff_dn"] / m["mean_dn_with"]),
           "| 99th percentile absolute difference, DN | %.1f |"
           % m["p99_abs_diff_dn"],
           "| pixels differing by more than 10 DN | %.4f |"
           % m["frac_px_over_10dn"],
           "| pixels differing by more than 100 DN | %.4f |"
           % m["frac_px_over_100dn"]]
    return out


def t_imgband(m):
    out = ["| band | merged band RMS with frame 46 | without | ratio |",
           "|---|---:|---:|---:|"]
    for b in m["band_rms"]:
        out.append("| L%d | %.4f | %.4f | **%.4f** |"
                   % (b["band"], b["with_46"], b["without"], b["ratio"]))
    return out


def tables():
    d = load("subgate.json")
    lad = load("subgate-ladder.json")
    g = load("rogue.json")
    m = load("rogue46.json")
    return dict(s2=t_s2(d["commission"]), s4=t_s4(d["commission"]),
                subgate=t_subgate(d), ladder=t_ladder(lad), dense=t_dense(g),
                conc=t_conc(g), f46=t_f46(g), rogue=t_rogue(g), img=t_img(m),
                imgband=t_imgband(m))


def values():
    d = load("subgate.json")
    lad = load("subgate-ladder.json")
    g = load("rogue.json")
    m = load("rogue46.json")
    s4 = d["commission"]["S4_selection_cost"]
    cb = lad["subjects"]["coffee-bubbles"]["rungs"][-1]
    bee = lad["subjects"]["bee-2-cpl@registered"]["rungs"][-1]
    rg = {r["band"]: r for r in g["rogue"]}
    f = g["f46"]
    return dict(
        s4_peak="The peak sits at signal fraction %.2f with a cost of %+.4f, "
                "and the endpoints read %+.4f and %+.4f"
                % (s4["argmax_sig_frac"], s4["peak"], s4["end_lo"],
                   s4["end_hi"]),
        cb_l4_n19="reaches **%+.3f at L4**" % band_of(cb["rows"],
                                                      4)["sel_cost"],
        pair_l5="%+.4f under the pair split" % band_of(bee["rows_pair"],
                                                      5)["sel_cost"],
        f46_dn="Frame 46 sits at %.1f DN against a stack median of %.1f -- "
               "**%.3fx, two stops dark** -- with %.3fx the per-frame noise."
               % (f["mean_dn"], f["stack_median_mean_dn"], f["mean_dn_ratio"],
                  f["std_dn_ratio"]),
        ship_l5="receives **%.5f of L5**" % rg[5]["shipping"],
        ship_l6="**%.5f of L6** under the shipping law" % rg[6]["shipping"],
        rmax75_l6="**%.5f at theta = 0.75**" % rg[6]["rmax0.75"],
        img_rms="%.1f DN" % m["rms_diff_dn"],
        img_l5="**%.4fx at L5**" % [b for b in m["band_rms"]
                                    if b["band"] == 5][0]["ratio"])


if __name__ == "__main__":
    t = tables()
    for k in sorted(t):
        print("<<<TABLE:%s>>>" % k)
        print("\n".join(t[k]))
        print()
    for k, v in sorted(values().items()):
        print("<<<VALUE:%s>>> %s" % (k, v))
