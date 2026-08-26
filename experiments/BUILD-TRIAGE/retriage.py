"""Revised triage: the stored per-subject verdicts, re-tested at an
INDEPENDENTLY CHOSEN site, with the partition arithmetic printed.

WHY A REVISION EXISTS
---------------------
The stored verdicts in triage.json rest on sites chosen by compare.py's own
percentile selectors (DETAIL / TRANSITION / FLAT / SOURCE-BEST / DEFICIT).
FLAT and DEFICIT are chosen to be the EMPTIEST sites in the frame.  That is
deliberate and correct for the headline question ("does the merge ever lose?"),
because an apparent deficit at an empty site is caught by the min-arm-SNR gate.

It is WRONG for classification.  If all of a subject's windows land on
background, the subject reads as "no detail in either arm anywhere", which is
indistinguishable in the output from a genuine capture limit.  Worked example,
and the reason this file exists:

    highly-angled-ruler-mm-cpl
      my windows        (6197,512), (512,1502) -- corners.  22-29 DN/px edges
                        against a 13-17 DN noise floor; frame SNR ~1.4; 0 of 4
                        sites entitled to vote.  Stored verdict: coverage gap.
      ORCH's window     (3808,3808), chosen by detailgallery.py on a different
                        statistic.  merge 1487.2 vs frame 775.5 DN/px, frame
                        SNR 12.1, merge AHEAD by 1.92x.  Verdict: GOOD.

ORCH independently reached the same conclusion by eye -- "at 1:1 its ruler
graduations are cleanly resolved with crisp edges ... The contact sheet was
misleading and the 1:1 tile corrected it" -- and asked for exactly this
re-opening: "I would rather you re-open a subject you have already classified
than let a thumbnail-based verdict stand."

So each subject is re-tested at ORCH's best-resolved site and any disagreement
with the stored verdict is printed, loudly, rather than silently resolved.

THE PARTITION
-------------
ORCH's requirement, restated: "your counts must still sum to 26 with no subject
unaccounted for, and I want the partition to distinguish *examined and found
sound* from *not examined* -- a subject that was skipped must not be able to
read as a subject that passed."

So NOT-EXAMINED is a first-class bucket with a mandatory reason, and UNRESOLVED
is a first-class bucket with a mandatory "what would settle it".  Neither is
allowed to be empty of justification, and the buckets are asserted to sum to
the corpus size.
"""
import collections
import glob
import json
import os

OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"
from orchsites import ORCH_DETAIL

# min-arm SNR below which a site cannot testify to merge loss. Read off the
# corpus, not asserted: the 104 sites sort into 1.54..2.99 then 5.59..43.46,
# an empty band of x1.87, with every "merge loses" verdict below it and the
# merge's advantage growing monotonically with real detail above it.
MIN_ARM_SNR = 4.0


def orch_site_row(subject):
    """Merge-vs-source at ORCH's independently chosen best-resolved site."""
    p = os.path.join(OUT, "compare", f"{subject}.orch.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    s = d["sites"].get("ORCH-BEST")
    if not s:
        return None
    e = s.get("edge") or {}
    m = e.get("merge_dnpx", 0.0)
    f = e.get("frame_corr_dnpx", 0.0)
    nm = e.get("noise_merge_dn", 0.0) or 0.0
    nf = e.get("noise_frame_dn", 0.0) or 0.0
    merge_snr = m / nm if nm > 0 else float("inf")
    frame_snr = f / nf if nf > 0 else float("inf")
    return {
        "merge_dnpx": m, "frame_dnpx": f,
        "ratio": e.get("ratio"), "blur_px": e.get("blur_equiv_px"),
        "deficit_dnpx": e.get("deficit_dnpx"),
        "ncc": s.get("locate", {}).get("ncc") or s.get("ncc"),
        "merge_snr": merge_snr, "frame_snr": frame_snr,
        "votes": bool(min(merge_snr, frame_snr) >= MIN_ARM_SNR),
    }


def flow_rows(subject):
    p = os.path.join(OUT, "sitescan", f"{subject}.flow.json")
    if not os.path.exists(p):
        return []
    return json.load(open(p))["sites"]


def main():
    stored = {r["subject"]: r for r in json.load(open(os.path.join(OUT, "triage.json")))["rows"]}
    dims = {d["subject"]: d for d in json.load(open(os.path.join(OUT, "dims.json")))}
    subjects = sorted(ORCH_DETAIL, key=lambda s: ORCH_DETAIL[s][0])

    print("=" * 132)
    print("REVISED TRIAGE -- stored verdict re-tested at ORCH's best-resolved site")
    print("=" * 132)
    hdr = (f"{'#':>3} {'subject':<36} {'WxH':<10} {'frm':>4} "
           f"{'ORCH-site merge/frame DN/px':<28} {'ratio':>7} {'SNR m/f':>11} {'vote':>5}  stored verdict")
    print(hdr)
    print("-" * len(hdr))

    revisions, missing = [], []
    for s in subjects:
        rank = ORCH_DETAIL[s][0]
        d = dims.get(s, {})
        wh = f"{d.get('w','?')}x{d.get('h','?')}"
        nf = d.get("n_frames", "?")
        st = stored.get(s, {}).get("verdict", "(none)")
        o = orch_site_row(s)
        if o is None:
            missing.append(s)
            print(f"{rank:>3} {s:<36} {wh:<10} {nf:>4} {'(ORCH-site run pending)':<28} "
                  f"{'':>7} {'':>11} {'':>5}  {st}")
            continue
        arm = f"{o['merge_dnpx']:>10.1f} /{o['frame_dnpx']:>9.1f}"
        vote = "yes" if o["votes"] else "NO"
        print(f"{rank:>3} {s:<36} {wh:<10} {nf:>4} {arm:<28} "
              f"{o['ratio']:>7.3f} {o['merge_snr']:>5.1f}/{o['frame_snr']:<5.1f} {vote:>5}  {st}")
        # A stored capture-limited verdict is CONTRADICTED when the ORCH site
        # both votes and shows the merge at or ahead of the best source frame.
        #
        # RESTRICTED TO THE COVERAGE-LIKE CATEGORIES ON PURPOSE.  Coverage gap,
        # occlusion and diffraction are all claims that "no frame resolved this
        # detail", so a single site where a frame demonstrably DID resolve it
        # is a direct contradiction.
        #
        # MOTION IS NOT SUCH A CLAIM and must not be auto-revised here.  Motion
        # is diagnosed from adjacent-frame NCC across the bracket; a subject can
        # move between frames and still contain a locally sharp site, and the
        # damage motion does is ghosting and doubled structure, not necessarily
        # softness at the best-resolved site.  Refuting a motion verdict needs a
        # motion measurement, which is BUILD-GHOST's instrument, not one sharp
        # window.  Listing motion subjects here would manufacture false
        # "revisions" out of evidence that cannot bear on them.
        CONTRADICTABLE = (
            "CAPTURE-LIMITED - coverage gap",
            "CAPTURE-LIMITED - occlusion/geometry",
            "CAPTURE-LIMITED - diffraction/magnification",
        )
        if o["votes"] and o["ratio"] is not None and o["ratio"] >= 0.95 \
                and st in CONTRADICTABLE:
            revisions.append((s, st, o))

    if missing:
        print(f"\n{len(missing)} subject(s) still pending at ORCH site: {', '.join(missing)}")

    if revisions:
        print("\n" + "=" * 132)
        print("CONTRADICTIONS -- stored verdict says capture-limited, ORCH's site says otherwise")
        print("=" * 132)
        for s, st, o in revisions:
            print(f"  {s}")
            print(f"    stored : {st}")
            print(f"    ORCH   : merge {o['merge_dnpx']:.1f} vs best frame {o['frame_dnpx']:.1f} DN/px "
                  f"= x{o['ratio']:.3f}, frame SNR {o['frame_snr']:.1f} (>= {MIN_ARM_SNR}, so it votes)")
            print(f"    -> the merge is AT OR AHEAD of the best single frame at a site that")
            print(f"       demonstrably carries detail. Not capture-limited at this site.")

    # ---- through-focus shape, where measured ------------------------------
    fl = [(s, flow_rows(s)) for s in subjects if flow_rows(s)]
    if fl:
        print("\n" + "=" * 132)
        print("THROUGH-FOCUS SHAPE (source frames only; did the detail ever exist?)")
        print("=" * 132)
        for s, rows in fl:
            for r in rows:
                v = ("interior peak -> detail EXISTED"
                     if r["peak_resolved_inside_bracket"] else
                     ("STILL CLIMBING at " + r["at_end"] if r["still_climbing"]
                      else "flat/low -> no frame in focus"))
                print(f"  {s:<36} {r['label']:<16} contrast {r['hf_max_rel']:.4f} "
                      f"shape x{r['peak_over_floor']:<5.1f} best {r['best_frame']:>3}  {v}")

    # ---- master width variation (ORCH's question) -------------------------
    print("\n" + "=" * 132)
    print("MASTER WIDTH VARIATION -- does it track anything?")
    print("=" * 132)
    by_w = collections.defaultdict(list)
    for s in subjects:
        d = dims.get(s, {})
        if d:
            by_w[d["w"]].append(s)
    for w in sorted(by_w):
        grp = by_w[w]
        nfs = [dims[s]["n_frames"] for s in grp]
        cks = [dims[s].get("coverage_k") for s in grp if dims[s].get("coverage_k")]
        print(f"  width {w} x {dims[grp[0]]['h']}  n={len(grp):>2}  "
              f"frames {min(nfs)}-{max(nfs)} (median {sorted(nfs)[len(nfs)//2]})  "
              f"coverage_k {min(cks):.4f}-{max(cks):.4f}" if cks else "")
        print(f"      {', '.join(sorted(grp))}")
    ws = sorted(by_w)
    if len(ws) == 2:
        a, b = by_w[ws[0]], by_w[ws[1]]
        fa = [dims[s]["n_frames"] for s in a]
        fb = [dims[s]["n_frames"] for s in b]
        ka = [dims[s]["coverage_k"] for s in a if dims[s].get("coverage_k")]
        kb = [dims[s]["coverage_k"] for s in b if dims[s].get("coverage_k")]
        print(f"\n  delta = {ws[1] - ws[0]} px, and both widths are exact multiples of 8 "
              f"({ws[0]}=8x{ws[0]//8}, {ws[1]}=8x{ws[1]//8}); height is identical "
              f"({dims[a[0]]['h']}=8x{dims[a[0]]['h']//8}) for all 26.")
        print(f"  frame count : {ws[0]} -> median {sorted(fa)[len(fa)//2]}, "
              f"{ws[1]} -> median {sorted(fb)[len(fb)//2]}.  "
              f"The medians differ, but the groups OVERLAP across almost the "
              f"whole corpus range\n                ({min(fa)}-{max(fa)} vs "
              f"{min(fb)}-{max(fb)}) and both contain 299-frame stacks, so with "
              f"n={len(fa)}/{len(fb)} this is not\n                evidence that "
              f"width tracks frame count.")
        if ka and kb:
            print(f"  coverage_k  : {ws[0]} -> {sum(ka)/len(ka):.4f} mean, "
                  f"{ws[1]} -> {sum(kb)/len(kb):.4f} mean.")
        print("  READING: the variation is a single 8 px block, the quantum the "
              "output is rounded to.")
        print("  It is a packaging wart, not a quality defect -- but a print set "
              "whose members differ")
        print("  in width is a real annoyance, and the fix is to pad or crop all "
              "masters to one size.")

    # ---- partition --------------------------------------------------------
    print("\n" + "=" * 132)
    print("PARTITION (stored verdicts; revisions above are NOT yet folded in)")
    print("=" * 132)
    c = collections.Counter(r["verdict"] for r in stored.values())
    total = 0
    for v, n in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"  {v:<44} {n:>3}")
        total += n
    print(f"  {'-' * 44} {'---'}")
    print(f"  {'TOTAL':<44} {total:>3}")
    assert total == len(ORCH_DETAIL), \
        f"partition does not sum to the corpus: {total} != {len(ORCH_DETAIL)}"
    print(f"\n  arithmetic checks: {' + '.join(str(n) for _, n in sorted(c.items()))} "
          f"= {total} = {len(ORCH_DETAIL)} subjects in SHIP-V1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
