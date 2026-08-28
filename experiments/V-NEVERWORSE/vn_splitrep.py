"""Emit section 9.24's tables from the split-half records.

WHY THIS EXISTS. Instrument defect #11 in section 9.23.12 was two table rows
transcribed into the report that had never been read out of a run -- I
extended a 1/N pattern and five of twelve cells were wrong. The verifier
caught it, but the cheaper fix is not to type numbers at all. Every row below
is printed from the JSON, and `vn_verify24.py` re-derives the same rows from
the same JSON, so the report, the generator and the checker all trace to one
record.

The derived quantities are computed HERE rather than in prose:

  manufactured  1 - recoh on flat pixels at L3: the share of the mid-scale
                band that is not reproducible across two independent halves.
  excess        shipping's flat mid-band VARIANCE divided by the plain mean's
                on the same pixels. Single render per arm, so no coherence
                relationship can move it.
  efficiency    flat mid-band variance per unit fine-band power. This is the
                blur-immune reading: an arm cannot improve it by throwing
                detail away, because the detail it throws away is the
                denominator. The plain mean's efficiency is the demonstration
                -- it wins on every raw mottle number in the table and loses
                this one by an order of magnitude.
"""
import io
import json
import os
import sys

SPLIT = r"C:\dev\strehl-out\V-NEVERWORSE\split"
ARMS = ("shipping", "confidence", "argmax", "mean")


def load(subj):
    with io.open(os.path.join(SPLIT, "%s.json" % subj), encoding="utf-8") as f:
        return json.load(f)


def row(d, arm, N):
    for r in d["rows"]:
        if r["arm"] == arm and r["N"] == N:
            return r
    return None


def at(r, level, key):
    for x in r.get("disc", []):
        if x["level"] == level:
            return x[key]
    return None


def derived(d, arm, N):
    r = row(d, arm, N)
    if r is None:
        return None
    rc = r["strat"].get("recoh_flat_L3")
    im = r["immune"]
    fv, fine = im.get("flatvar_L3"), im["fine"]
    mn = row(d, "mean", N)
    base = mn["immune"].get("flatvar_L3") if mn else None
    return dict(
        arm=arm, N=N,
        soft=at(r, 3, "disc_soft"), hard=at(r, 3, "disc_step"),
        recoh=r["recoh"]["3"], recoh_flat=rc,
        recoh_det=r["strat"].get("recoh_detail_L3"),
        manufactured=(1.0 - rc) if rc is not None else None,
        flatvar=fv, fine=fine, blotch=im["blotch"],
        excess=(fv / base) if (fv and base) else None,
        efficiency=(fv / fine) if (fv and fine) else None,
        refused="refused" in r)


def admit(d):
    """Which statistics survived their own planted defect on THIS subject.

    Read out of the record, never assumed. A statistic that failed its plant
    is printed as REFUSED in every table rather than omitted, so a reader
    counting rows cannot mistake a statistic that was never commissioned for
    one that was measured and came out unremarkable.
    """
    return d["commission"]["arms"].get("admit", {})


def cell(d, key, val, spec):
    if not admit(d).get(key, False):
        return "REFUSED"
    if val is None:
        return "n/a"
    return spec % val


def table_ladder(d):
    out = ["| arm | N | soft L3 | recoh all | recoh flat | recoh detail | "
           "blotch | fine |",
           "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for arm in ARMS:
        for N in d["ks"]:
            g = derived(d, arm, N)
            if g is None:
                continue
            out.append("| %s | %d | %s | %s | %s | %s | %s | %s |"
                       % (arm, N,
                          "REFUSED" if g["refused"]
                          else cell(d, "soft", g["soft"], "%.4f"),
                          cell(d, "recoh_all", g["recoh"], "%.4f"),
                          cell(d, "recoh_flat", g["recoh_flat"], "%.4f"),
                          cell(d, "recoh_detail", g["recoh_det"], "%.4f"),
                          cell(d, "blotch", g["blotch"], "%.5f"),
                          cell(d, "fine", g["fine"], "%.4g")))
    return out


def table_manufactured(d):
    out = ["| arm | N | manufactured | flat mid-band var | x plain mean | "
           "fine | var/fine |",
           "|---|--:|--:|--:|--:|--:|--:|"]
    for N in d["ks"]:
        for arm in ARMS:
            g = derived(d, arm, N)
            if g is None or g["flatvar"] is None:
                continue
            out.append("| %s | %d | %s | %s | %s | %s | %s |"
                       % (arm, N,
                          cell(d, "recoh_flat", g["manufactured"], "%.4f"),
                          cell(d, "flatvar", g["flatvar"], "%.1f"),
                          cell(d, "flatvar", g["excess"], "%.2fx"),
                          cell(d, "fine", g["fine"], "%.4g"),
                          cell(d, "efficiency", g["efficiency"], "%.4g")))
    return out


def table_ceiling(d):
    out = ["| N | twin soft (no focus info) | shipping soft | obs/ceiling |",
           "|--:|--:|--:|--:|"]
    for N in d["ks"]:
        c = d["ceiling"][str(N)]
        g = derived(d, "shipping", N)
        out.append("| %d | %s | %s | %s |"
                   % (N,
                      cell(d, "soft", c["disc_soft"], "%.4f"),
                      cell(d, "soft", g["soft"], "%.4f"),
                      cell(d, "soft",
                           g["soft"] / max(c["disc_soft"], 1e-9), "%.4f")))
    return out


def headline(d):
    """The four numbers section 9.24 turns on, all from the record."""
    top = d["ks"][0]
    sh = derived(d, "shipping", top)
    fx = derived(d, "confidence", top)
    mn = derived(d, "mean", top)
    ax = derived(d, "argmax", top)
    c = d["ceiling"][str(top)]
    A = admit(d)

    def g(key, v):
        return v if A.get(key, False) else "REFUSED"

    out = dict(
        subject=d["subject"], N=top,
        twin_ratio=g("soft", sh["soft"] / max(c["disc_soft"], 1e-9)),
        excess=g("flatvar", sh["excess"]),
        excess_ladder=g("flatvar",
                        [derived(d, "shipping", N)["excess"]
                         for N in sorted(d["ks"])]),
        manufactured=g("recoh_flat", sh["manufactured"]),
        fix_removes_fraction=g(
            "recoh_flat",
            (sh["manufactured"] - fx["manufactured"]) / sh["manufactured"]),
        fix_removes_variance=g("flatvar",
                               1.0 - fx["flatvar"] / sh["flatvar"]),
        fix_fine_cost=g("fine", 1.0 - fx["fine"] / sh["fine"]),
        fix_efficiency_gain=g("efficiency",
                              1.0 - fx["efficiency"] / sh["efficiency"]),
        mean_efficiency_ratio=g("efficiency",
                                mn["efficiency"] / sh["efficiency"]),
        mean_fine_retained=g("fine", mn["fine"] / sh["fine"]),
        argmax_efficiency_ratio=g("efficiency",
                                  ax["efficiency"] / sh["efficiency"]),
        admitted="%d/%d %s" % (sum(A.values()), len(A),
                               ",".join(sorted(k for k in A if not A[k]))
                               or "(none refused)"),
        hard_spread=d["commission"]["arms"]["hard_spread"],
        hard_ship=sh["hard"], hard_fix=fx["hard"], hard_argmax=ax["hard"],
        hard_ship_minus_fix=abs(sh["hard"] - fx["hard"]),
        blur_breakdown_sigma=d["commission"]["arms"]["margins"].get(
            "blur_breakdown_sigma"),
        margins={k: v for k, v in
                 d["commission"]["arms"]["margins"].items()
                 if not k.startswith("blur")},
        naive_on_perfect=d["commission"]["metric"]["naive_on_perfect_input"],
        floor_slope=d["floor"]["slope"], floor_r2=d["floor"]["r2"],
        counts=d["counts"])
    return out


def table_orch(d):
    """What ORCH's test, as stated, would read before and after the fix.

    The left column is the statistic ORCH asked for: the rate at which the
    merge's per-pixel FRAME CHOICE disagrees between two independent halves.
    The right columns are statistics that respond to selectivity. If the left
    column is flat across arms that differ enormously on the right, the test
    as stated cannot grade the fix.
    """
    out = ["| arm | N | ORCH: hard frame-choice discordance | soft (weight "
           "centroid) | flat mid-band var | fine |",
           "|---|--:|--:|--:|--:|--:|"]
    for arm in ("shipping", "confidence", "argmax"):
        for N in d["ks"]:
            g = derived(d, arm, N)
            if g is None or g["hard"] is None:
                continue
            out.append("| %s | %d | %.4f | %s | %s | %s |"
                       % (arm, N, g["hard"],
                          cell(d, "soft", g["soft"], "%.4f"),
                          cell(d, "flatvar", g["flatvar"], "%.1f"),
                          cell(d, "fine", g["fine"], "%.4g")))
    return out


def table_hardspread(ds):
    out = ["| subject | N | hard-winner discordance at p=1 | p=2 | p=4 | "
           "spread | soft at p=2 | soft at p=4 |",
           "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for d in ds:
        a = d["commission"]["arms"]
        h = [a[t]["disc"]["disc_step"] for t in ("improve", "base", "defect")]
        s = [a[t]["stats"]["soft"] for t in ("base", "defect")]
        out.append("| %s | %d | %.4f | %.4f | %.4f | %.2e | %.4f | %.4f |"
                   % (d["subject"], d["ks"][0], h[0], h[1], h[2],
                      a["hard_spread"], s[0], s[1]))
    return out


def table_metric(d):
    out = ["| arm | region | soft | hard | naive rank | recoh | median steps "
           "| admitted |", "|---|---|--:|--:|--:|--:|--:|--:|"]
    m = d["commission"]["metric"]
    for arm in ("noisefree", "noisy"):
        for reg in ("textured_L2", "textured_L3", "flat_L2", "flat_L3"):
            r = m.get("%s_%s" % (arm, reg))
            if r is None:
                continue
            out.append("| %s | %s | %.4f | %.4f | %.4f | %.4f | %.2f | %.3f |"
                       % (arm, reg, r["disc_soft"], r["disc_step"],
                          r["disc_rank"], r["recoh"], r["med_steps"],
                          r["both_admitted"]))
    return out


def table_margins(ds):
    keys = ("soft", "blotch", "flatvar", "recoh_all", "recoh_flat",
            "recoh_detail")
    out = ["| statistic | " + " | ".join(
        "%s defect / improve" % d["subject"] for d in ds) + " | admitted on |",
        "|---|" + "--:|" * len(ds) + ":-:|"]
    for k in keys:
        cells, n_ok = [], 0
        for d in ds:
            m = d["commission"]["arms"]["margins"][k]
            ok = admit(d).get(k, False)
            n_ok += 1 if ok else 0
            cells.append("%+.4f%% / %+.4f%%" % (100 * m[0], 100 * m[1]))
        out.append("| `%s` | %s | %d of %d |"
                   % (k, " | ".join(cells), n_ok, len(ds)))
    return out


def table_blur(d):
    out = ["| blur sigma px | fine | flat mid-band var | var/fine "
           "(must worsen) | fires |", "|--:|--:|--:|--:|:-:|"]
    for s in d["commission"]["arms"]["margins"]["blur_sweep"]:
        out.append("| %.2f | %+.2f%% | %+.2f%% | %+.2f%% | %s |"
                   % (s["sigma"], 100 * s["d_fine"], 100 * s["d_var"],
                      100 * s["d_eff"], "yes" if s["fires"] else "no"))
    return out


def table_fix(ds):
    out = ["| subject | N | flat mid-band var removed | fine band cost | "
           "blur-immune var/fine gain | verdict |",
           "|---|--:|--:|--:|--:|---|"]
    for d in ds:
        h = headline(d)
        v, f, e = (h["fix_removes_variance"], h["fix_fine_cost"],
                   h["fix_efficiency_gain"])
        if isinstance(v, str) or isinstance(f, str):
            out.append("| %s | %d | %s | %s | %s | REFUSED |"
                       % (d["subject"], h["N"], v, f, e))
            continue
        out.append("| %s | %d | %.1f%% | %.1f%% | %.1f%% | %s |"
                   % (d["subject"], h["N"], 100 * v, 100 * f, 100 * e,
                      "pays for itself" if e > f else
                      "costs more sharpness than it buys cleanliness"))
    return out


def table_antiblur(ds):
    out = ["| subject | arm | blotch | flat mid-band var | fine | var/fine | "
           "vs shipping |", "|---|---|--:|--:|--:|--:|--:|"]
    for d in ds:
        N = d["ks"][0]
        sh = derived(d, "shipping", N)
        for arm in ("shipping", "mean"):
            g = derived(d, arm, N)
            out.append("| %s | %s | %s | %s | %s | %s | %s |"
                       % (d["subject"], arm,
                          cell(d, "blotch", g["blotch"], "%.5f"),
                          cell(d, "flatvar", g["flatvar"], "%.1f"),
                          cell(d, "fine", g["fine"], "%.4g"),
                          cell(d, "efficiency", g["efficiency"], "%.4g"),
                          "--" if arm == "shipping" else
                          cell(d, "efficiency",
                               g["efficiency"] / sh["efficiency"],
                               "%.2fx WORSE")))
    return out


def values(ds):
    """Scalar facts quoted inline in the prose, computed from the records.

    Inline numbers are where transcription errors live -- a table is generated
    but a sentence is typed. Drafting this section I wrote "five of the nine"
    for the wrong-way count and the true value was six. Anything quoted in a
    sentence now comes from here.
    """
    recohs = ("recoh_all", "recoh_flat", "recoh_detail")
    wrong = sum(1 for d in ds for k in recohs
                if d["commission"]["arms"]["margins"][k][0] < 0)
    total = len(ds) * len(recohs)
    cb = ds[0]
    return dict(
        wrongway="%d of the %d" % (wrong, total),
        naive="%.4f" % cb["commission"]["metric"]["naive_on_perfect_input"],
        nsubj=str(len(ds)),
        nframes=", ".join(str(d["ks"][0]) for d in ds),
        twin_ratios=", ".join(
            "%.3f" % headline(d)["twin_ratio"] for d in ds),
        blur_sigma="%.2f" % cb["commission"]["arms"]["margins"][
            "blur_breakdown_sigma"],
        hard_equal="%.16f" % headline(ds[1])["hard_ship"],
        hard_diff="%.1f" % headline(ds[1])["hard_ship_minus_fix"],
        mean_fine=", ".join(
            "%.2f%%" % (100 * headline(d)["mean_fine_retained"]) for d in ds),
        mean_eff=", ".join(
            "%.2fx" % headline(d)["mean_efficiency_ratio"] for d in ds),
        fix_var=", ".join(
            "%.1f%%" % (100 * headline(d)["fix_removes_variance"])
            for d in ds),
        fix_fine=", ".join(
            "%.1f%%" % (100 * headline(d)["fix_fine_cost"]) for d in ds),
        fix_eff=", ".join(
            "%+.1f%%" % (100 * headline(d)["fix_efficiency_gain"])
            for d in ds),
        excess=", ".join("%.2fx" % headline(d)["excess"] for d in ds),
        mean_floor=", ".join(
            "%.1f" % derived(d, "mean", N)["flatvar"]
            for d in [ds[0]] for N in sorted(ds[0]["ks"])),
        soft_margins=", ".join(
            "%.1f%%" % (100 * d["commission"]["arms"]["margins"]["soft"][0])
            for d in ds),
    )


def emit(path, ds):
    """Substitute every <<<TABLE:name>>> and <<<VALUE:name>>> marker in the
    prose. A marker with no generator is an error and an unused generator is
    an error, so a table can be neither lost by a typo nor silently dropped."""
    import re
    gen = dict(hardspread=lambda: table_hardspread(ds),
               orch=lambda: table_orch(ds[1]),
               metric=lambda: table_metric(ds[0]),
               margins=lambda: table_margins(ds),
               blur=lambda: table_blur(ds[0]),
               ladder=lambda: table_ladder(ds[0]),
               manufactured=lambda: table_manufactured(ds[0]),
               corpus=lambda: table_corpus(ds),
               ceiling=lambda: table_ceiling(ds[0]),
               fix=lambda: table_fix(ds),
               antiblur=lambda: table_antiblur(ds))
    val = values(ds)
    with io.open(path, encoding="utf-8") as f:
        txt = f.read()
    seen = set()
    for m in re.findall(r"<<<TABLE:(\w+)>>>", txt):
        if m not in gen:
            raise SystemExit("no generator for table '%s'" % m)
        seen.add(m)
        txt = txt.replace("<<<TABLE:%s>>>" % m, "\n".join(gen[m]()))
    missing = set(gen) - seen
    if missing:
        raise SystemExit("generators never used: %s" % sorted(missing))
    for m in re.findall(r"<<<VALUE:(\w+)>>>", txt):
        if m not in val:
            raise SystemExit("no value for '%s'" % m)
        txt = txt.replace("<<<VALUE:%s>>>" % m, val[m])
    left = re.findall(r"<<<[^>]*>>>", txt)
    if left:
        raise SystemExit("unsubstituted markers: %s" % left)
    return txt


def table_corpus(ds):
    """One row per subject: the numbers section 9.24's verdict rests on.

    Every column is a WITHIN-subject comparison. `excess` divides shipping by
    the plain mean on the same pixels of the same subject; `twin` divides
    shipping by a no-focus-information twin built from the same frames. None
    of these may be compared across subjects as levels -- the discordance
    floor is set by how much of a subject is flat, which is a property of the
    subject and not of the merge (section 9.24.2). What IS comparable across
    subjects is the SIGN and the DIRECTION of each ladder.
    """
    out = ["| subject | N | sigma DN | shipping excess | excess at min N | "
           "rises with N | twin ratio | manufactured | fix var | fix fine |",
           "|---|--:|--:|--:|--:|:-:|--:|--:|--:|--:|"]

    def s(v, spec):
        return v if isinstance(v, str) else spec % v

    for d in ds:
        h = headline(d)
        lad = h["excess_ladder"]
        ok = isinstance(lad, list)
        out.append("| %s | %d | %.3f | %s | %s | %s | %s | %s | %s | %s |"
                   % (d["subject"], h["N"], d["sigma"],
                      s(h["excess"], "%.2fx"),
                      s(lad[0] if ok else lad, "%.2fx"),
                      ("yes" if lad == sorted(lad) and lad[-1] > lad[0]
                       else "NO") if ok else "REFUSED",
                      s(h["twin_ratio"], "%.4f"),
                      s(h["manufactured"], "%.4f"),
                      s(h["fix_removes_variance"], "%.1f%%")
                      if isinstance(h["fix_removes_variance"], str)
                      else "%.1f%%" % (100 * h["fix_removes_variance"]),
                      s(h["fix_fine_cost"], "%.1f%%")
                      if isinstance(h["fix_fine_cost"], str)
                      else "%.1f%%" % (100 * h["fix_fine_cost"])))
    return out


def main():
    argv = list(sys.argv[1:])
    prose = None
    if "--emit" in argv:
        i = argv.index("--emit")
        prose = argv[i + 1]
        del argv[i:i + 2]
    subs = argv or ["coffee-bubbles"]
    loaded = []
    for s in subs:
        d = load(s)
        loaded.append(d)
    if prose:
        sys.stdout.write(emit(prose, loaded))
        return 0
    for d in loaded:
        s = d["subject"]
        print("\n### %s  (n=%d, %dx%d, sigma %.3f DN)"
              % (s, d["n"], d["shape"][0], d["shape"][1], d["sigma"]))
        print("\nLADDER")
        print("\n".join(table_ladder(d)))
        print("\nMANUFACTURED / ANTI-BLUR")
        print("\n".join(table_manufactured(d)))
        print("\nCEILING")
        print("\n".join(table_ceiling(d)))
        print("\nWHAT ORCH'S TEST WOULD READ")
        print("\n".join(table_orch(d)))
        print("\nHEADLINE")
        h = headline(d)
        for k in sorted(h):
            print("  %-24s %s" % (k, h[k]))
    if len(loaded) > 1:
        print("\n### CORPUS")
        print("\n".join(table_corpus(loaded)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
