"""Emit section 3 of the report directly from triage.json + the compare JSONs.

Hand-transcribing 26 rows invites a number that disagrees with the artefact it
came from, so the table is generated.  ASCII only.
"""
import json, os, tri

SNR = 4.0
def usable(v):
    if any("not clear of" in c for c in v.get("caution", [])):  return False
    if not v.get("reliable", True):                             return False
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0), e.get("frame_corr_dnpx", 0)
    nm, nf = e.get("noise_merge_dn", 0), e.get("noise_frame_dn", 0)
    if nm > 0 and m < SNR * nm:                                 return False
    if e.get("ratio", 1) < 1.0 and nf > 0 and f < SNR * nf:     return False
    return True

doc = json.load(open(os.path.join(tri.OUT, "triage.json"), encoding="utf-8"))
rows = {r["subject"]: r for r in doc["rows"]}
counts = doc["counts"]
SH = {"GOOD": "GOOD",
      "MERGE-LIMITED": "MERGE-LIMITED",
      "CAPTURE-LIMITED - coverage gap": "CAP: coverage gap",
      "CAPTURE-LIMITED - occlusion/geometry": "CAP: occluded geometry",
      "CAPTURE-LIMITED - diffraction/magnification": "CAP: diffraction",
      "CAPTURE-LIMITED - motion": "CAP: motion",
      "UNRESOLVED": "UNRESOLVED"}
ORDER = list(SH)
missing = sorted({r["verdict"] for r in doc["rows"]} - set(ORDER))
assert not missing, f"verdict(s) absent from the table vocabulary: {missing}"

L = ["## 3. Triage table", ""]
L.append("All 26 subjects. `merge` and `best frame` are edge slope in **DN/px**,")
L.append("measured on camera-linear renders of *both* arms, at the same site, over")
L.append("the same window, with the source frame carried through the identical")
L.append("alignment gather (section 1.2). The pair quoted is the subject's *worst*")
L.append("evidence-bearing site -- the one most favourable to a merge-loss verdict.")
L.append("`deficit` is positive when the source frame is ahead of the merge (a")
L.append("defect) and negative when **the merge beats every single source frame**.")
L.append("`worst px` is the equivalent Gaussian softening; the instrument floor is")
L.append("0.30 px, so any value at or below that is *no measurable difference*.")
L.append("")
L.append("| # | subject | verdict | WxH | merge DN/px | best frame DN/px | deficit DN/px | worst px | evidence |")
L.append("|---:|---|---|---|---:|---:|---:|---:|---|")

n = 0
for cat in ORDER:
    for s in sorted(k for k, r in rows.items() if r["verdict"] == cat):
        r = rows[s]; e = r["evidence"]
        d = json.load(open(os.path.join(tri.OUT, "compare", s + ".json")))
        best = None
        for lab, v in d["sites"].items():
            if lab == "FLAT" or not usable(v):  continue
            ed = v["edge"]
            dfc = ed["frame_corr_dnpx"] - ed["merge_dnpx"]
            if best is None or dfc > best[0]:
                best = (dfc, ed["merge_dnpx"], ed["frame_corr_dnpx"], lab)
        n += 1
        if best:
            dfc, m, f, lab = best
            pct = 100.0 * dfc / max(f, 1e-9)
            cells = (f"{m:.0f} | {f:.0f} | {dfc:+.1f} | "
                     f"{float(e.get('worst_blur_px') or 0.0):.2f}")
            at = f"at {lab}, {pct:+.1f}%"
        else:
            cells = "-- | -- | -- | --"
            at = "no site had signal over noise in either arm"
        if cat == "GOOD":
            ev = at
        elif cat.endswith("coverage gap"):
            e0, eN = e.get("end0_pct") or 0.0, e.get("endN_pct") or 0.0
            end = "first" if e0 >= eN else "last"
            ev = (f"{e['detail_gap_pct']:.2f}% of detail-bearing pixels elect "
                  f"the **{end}** frame ({e['detail_enrichment']:.2f}x its own "
                  f"shuffled null; {e['boundary_pct']:.2f}% of all pixels); {at}")
        elif cat.endswith("occlusion/geometry"):
            ev = (f"{e['detail_gap_pct']:.2f}% of detail-bearing pixels at a "
                  f"bracket end ({e['detail_enrichment']:.2f}x null), but on "
                  f"occlusion edges, not a short bracket; {at}")
        elif cat.endswith("motion"):
            ev = (f"NCC {e['motion_med_ncc']:.5f}, {e['motion_blocks']}/24 "
                  f"blocks moving; {at}")
        else:
            ev = (r.get("why") or [at])[0].replace("|", "/")
        dim = f"{e.get('master_w')}x{e.get('master_h')}"
        L.append(f"| {n} | `{s}` | **{SH[cat]}** | {dim} | {cells} | {ev} |")

L += ["", "### 3.1 The arithmetic", "", "```"]
for cat in ORDER:
    L.append(f"{counts.get(cat, 0):>5}  {cat}")
tot = sum(counts.get(c, 0) for c in ORDER)
L += ["  ---", f"{tot:>5}  TOTAL", "```", ""]
L.append("    " + "  +  ".join(str(counts.get(c, 0)) for c in ORDER) + f"  =  {tot}")
L += ["", "The zero rows are printed on purpose. A count that does not move "
      "looks identical whether nothing was wrong or nothing was examined, so "
      "`MERGE-LIMITED 0`, `CAP: diffraction 0` and `UNRESOLVED 0` are stated "
      "rather than omitted.", ""]
L += ["### 3.2 What each class needs", "",
      "| verdict | n | who fixes it | action |", "|---|---:|---|---|"]
ACT = {
 "GOOD": ("nobody", "ship as-is"),
 "MERGE-LIMITED": ("the software", "route to the merge; source frames hold "
                   "detail the merge discarded"),
 "CAPTURE-LIMITED - coverage gap": ("the camera", "reshoot extending the "
   "bracket past the stated end. The end is named per subject in the table and "
   "on the contact sheet, so this is actionable without re-measuring. The merge "
   "cannot invent focus no frame captured."),
 "CAPTURE-LIMITED - occlusion/geometry": ("nobody, with frames", "**more "
   "frames will not help.** The unresolved pixels are occluded from the lens, "
   "not out of focus, so extending the bracket changes nothing. Reshoot from "
   "another angle or accept the subject's geometry."),
 "CAPTURE-LIMITED - diffraction/magnification": ("the camera", "reshoot at a "
   "wider marked aperture"),
 "CAPTURE-LIMITED - motion": ("the camera", "shorten the bracket or stabilise; "
   "no merge change recovers a subject that moved"),
 "UNRESOLVED": ("nobody yet", "re-site the comparison; not a statement about "
                "the image"),
}
for cat in ORDER:
    who, act = ACT[cat]
    L.append(f"| {SH[cat]} | {counts.get(cat, 0)} | {who} | {act} |")
print("\n".join(L))
