"""Corpus-wide absolute merge-vs-source ledger over evidence-bearing sites."""
import json, os, tri

SNR = 4.0
def usable(v):
    if any("not clear of" in c for c in v.get("caution", [])):
        return False
    if not v.get("reliable", True):
        return False
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0), e.get("frame_corr_dnpx", 0)
    nm, nf = e.get("noise_merge_dn", 0), e.get("noise_frame_dn", 0)
    if nm > 0 and m < SNR * nm:
        return False
    if e.get("ratio", 1) < 1.0 and nf > 0 and f < SNR * nf:
        return False
    return True

rows, nsite, nloss = [], 0, 0
for s in tri.SUBJECTS:
    d = json.load(open(os.path.join(tri.OUT, "compare", s + ".json")))
    worst = None
    for lab, v in d["sites"].items():
        if lab == "FLAT" or not usable(v):
            continue
        e = v["edge"]
        nsite += 1
        # deficit_dnpx is POSITIVE when the source is ahead of the merge.
        dfc = e["frame_corr_dnpx"] - e["merge_dnpx"]
        if dfc > 0:
            nloss += 1
        pct = 100.0 * dfc / max(e["frame_corr_dnpx"], 1e-9)
        if worst is None or dfc > worst[1]:
            worst = (lab, dfc, pct, e["merge_dnpx"], e["frame_corr_dnpx"],
                     e["ratio"], e["blur_equiv_px"])
    if worst:
        rows.append((s,) + worst)

rows.sort(key=lambda r: -r[2])
print("MERGE-vs-BEST-SOURCE, worst evidence-bearing site per subject")
print("positive deficit = SOURCE ahead of merge (a defect); negative = merge ahead")
print()
print(f"{'subject':<38}{'site':<12}{'merge':>9}{'source':>9}{'deficit':>9}"
      f"{'%':>8}{'blur px':>9}")
for s, lab, dfc, pct, m, f, rat, bl in rows:
    print(f"{s:<38}{lab:<12}{m:>9.0f}{f:>9.0f}{dfc:>+9.1f}{pct:>+8.1f}{bl:>9.2f}")
print()
print(f"evidence-bearing sites: {nsite}   of which source ahead: {nloss}")
w = max(rows, key=lambda r: r[3])
print(f"WORST absolute deficit anywhere: {w[2]:+.1f} DN/px ({w[3]:+.1f}%) "
      f"on {w[0]} at {w[1]}")
ahead = [r for r in rows if r[2] < 0]
print(f"subjects whose worst site still has the MERGE ahead: {len(ahead)}/{len(rows)}")
