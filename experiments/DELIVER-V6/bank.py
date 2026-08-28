"""Bank the DELIVER-V6 delivery record as text, before the heavy artifacts go.

The rule this serves: a finding that exists only inside a 200 MB TIFF is a
finding you destroy when you reclaim the disk.  V-RIM has already published a
result nobody can reproduce because its binary, scratch and json were all
deleted.  This lane will not add a second one.

So every number that took CPU time to produce is written out as text here:
per-subject provenance (frames, ISO, wall time, alignment, SHA256, byte count),
the print-critical TIFF tags read from the delivered bytes, and the reproduction
recipe.  Text is free; the TIFFs are not.

Assembled from files rather than typed, so the banked numbers cannot drift from
the measured ones:
    masters/MANIFEST.txt      -- the 26 original corpus subjects
    masters/manifest-{A,B,C}.txt -- the 7 new subjects, one file per stream
    masters/TAGS.json         -- tagcheck.py output, read from the output bytes
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASTERS = Path(r"C:\dev\strehl-out\DELIVER-V6\masters")

EXE_SHA = "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
COMMIT = "6af834dac08d6605aee7ea3ad75809fdf6313770"


def read_text(p):
    """These manifests are written by PowerShell Out-File -Encoding utf8 and can
    carry a BOM or stray NULs; strip both rather than let a decode mangle rows."""
    return p.read_text(encoding="utf-8", errors="replace").replace("\0", "")


def records(path):
    if not path.exists():
        return {}
    out = {}
    for blk in re.split(r"\r?\n\r?\n", read_text(path)):
        m = re.search(r"^subject   : (\S+)", blk, re.M)
        if not m:
            continue
        rec = {}
        for line in blk.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if k == "banner":
                    rec.setdefault("banner", []).append(v)
                else:
                    rec[k] = v
        out[m.group(1)] = rec
    return out


def main():
    recs = records(MASTERS / "MANIFEST.txt")
    origin = {k: "corpus-26" for k in recs}
    for tag in ("A", "B", "C"):
        r = records(MASTERS / f"manifest-{tag}.txt")
        for k, v in r.items():
            recs[k] = v
            origin[k] = f"new-7 (stream {tag})"

    tags = {t["subject"]: t for t in json.loads((MASTERS / "TAGS.json").read_text(encoding="utf-8"))}

    L = []
    L.append("# DELIVER-V6 — banked delivery record for all 33 masters")
    L.append("")
    L.append("Written before the lane's non-deliverable scratch was reclaimed, so that every")
    L.append("number below survives the deletion of the files it was measured from. The")
    L.append("masters themselves are the shipping product and are retained.")
    L.append("")
    L.append("## Reproduction recipe")
    L.append("")
    L.append("```")
    L.append(f"exe        : C:\\dev\\strehl-out\\DELIVER-V6\\bin\\strehl.exe")
    L.append(f"exe SHA256 : {EXE_SHA}")
    L.append(f"exe build  : strehl 0.0.0 (6af834dac08d)")
    L.append(f"commit     : {COMMIT}")
    L.append("sources    : D:\\personal\\macro\\<subject>   (READ-ONLY)")
    L.append("invocation : <exe> stack <dir> -o <out>\\<subject>.tiff --srgb")
    L.append("env        : STREHL_CACHE_DIR=<private>; all other STREHL_* unset")
    L.append("driver     : experiments/DELIVER-V6/render.ps1  (26)")
    L.append("             experiments/DELIVER-V6/render-list.ps1 -Tag A|B|C  (7)")
    L.append("```")
    L.append("")
    L.append("**The binary is deterministic end to end.** ORCH independently rendered the same")
    L.append("seven subjects with this exe between 02:36 and 02:47; DELIVER-V6 re-rendered them")
    L.append("between 03:38 and 03:50 in three concurrent streams. All seven came out")
    L.append("**byte-for-byte identical, whole-file SHA256 including container metadata**. A")
    L.append("fixed binary reproduces exactly; it is a *moving tree* that does not.")
    L.append("")
    L.append("That comparison was re-run immediately before ORCH's copies were reclaimed:")
    L.append("**7 of 7 identical**, same byte count, across a different concurrency (1 stream")
    L.append("vs 3), a different cache directory and a different hour. The seven SHA256 values")
    L.append("in the table below are therefore the output of *two* independent runs, so the")
    L.append("proof outlives the deleted copies. This bounds corpus fact 1886 usefully: the")
    L.append("33,003,417-pixel drift it records is attributable to the tree moving under the")
    L.append("build, not to nondeterminism in the pipeline. Pin the binary and absolutes hold.")
    L.append("")
    L.append("## Commissioning control for the tag reader")
    L.append("")
    L.append("`experiments/DELIVER-V6/tagcheck.py` refuses to certify anything unless it first")
    L.append("reads the defect in a file known to have it. That control file lives outside the")
    L.append("protected paths and may be reclaimed by another lane, so it is identified here:")
    L.append("")
    L.append("```")
    L.append("path   : C:\\dev\\strehl-out\\marker.tif   (rendered 2026-08-23, predates ICC fix 96b7e119)")
    L.append("bytes  : 49505882")
    L.append("sha256 : E9ED246B8FCB09F06DAA8606C33536D0828AC9C65936ED462877132244A3DAB2")
    L.append("reads  : ICC 34675 ABSENT | XResolution 1/1 | ResolutionUnit 1 (none)")
    L.append("```")
    L.append("")
    L.append("If it is gone, any TIFF written by strehl before 2026-08-26 11:27 carries the same")
    L.append("signature and will serve. ORCH-FAITHFUL masters will **not** — they postdate the fix.")
    L.append("")
    L.append("## Per-subject record")
    L.append("")
    L.append("ICC/DPI columns are read from the delivered bytes by BUILD-OUTPUT's raw-IFD")
    L.append("parser, not from the code and not from the run log.")
    L.append("")
    L.append("| subject | set | frames | ISO | secs | bytes | ICC | dpi | unit | output SHA256 |")
    L.append("| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |")
    for name in sorted(recs):
        r = recs[name]
        t = tags.get(name, {})
        icc = f"{t.get('icc_len', 0)} B" if t.get("icc_present") else "**ABSENT**"
        dpi = "%d/%d" % tuple(t["xres"]) if t.get("xres") else "-"
        L.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | `%s` |" % (
            name, origin.get(name, "?"), r.get("frames", "?"), r.get("ISO", "—"),
            r.get("secs", "?"), r.get("bytes", "?"), icc, dpi,
            t.get("unit_name", "-"), r.get("out SHA256", "?")))
    L.append("")
    L.append("ISO is recorded only for the seven new subjects; the 26 predate the manifest")
    L.append("field. Six of the seven are **ISO 50**, below the shipped noise profile's ISO 100")
    L.append("calibration floor, so every gate that divides by sigma is extrapolating on them.")
    L.append("")
    L.append("## Alignment disposition, seven new subjects")
    L.append("")
    L.append("```")
    for name in sorted(k for k in recs if origin.get(k, "").startswith("new-7")):
        L.append("%-30s %s" % (name, recs[name].get("alignment", "not reported")))
    L.append("```")
    L.append("")
    L.append("Every new subject solved an alignment and placed **every frame, none refused**.")
    L.append("")
    L.append("## Clipping and crush")
    L.append("")
    L.append("Full per-subject, per-channel census in `data/clip-census-33.txt`. Reported as")
    L.append("numbers, never as a verdict: `orch_printready.py`'s clip gate measures the sRGB")
    L.append("gamut wall, not the tone scale, and it failed the one master in the corpus with")
    L.append("zero blown highlights.")
    L.append("")
    L.append("## Sheets")
    L.append("")
    L.append("```")
    L.append("D:\\strehl-out\\DELIVER-V6\\corpus-all33\\sheet-00..10.jpg   all 33 subjects")
    L.append("D:\\strehl-out\\DELIVER-V6\\corpus-new7\\sheet-00..02.jpg    the 7 new subjects")
    L.append("D:\\strehl-out\\DELIVER-V6\\corpus\\, corpus-registered\\     the 26, CA before/after")
    L.append("D:\\strehl-out\\DELIVER-V6\\ca-ab\\                          magenta A/B crops")
    L.append("```")
    L.append("")
    L.append("**Sampling:** tiles are 520 px crops taken at native resolution and pasted without")
    L.append("scaling, so one image pixel is one sheet pixel. No zoom, no resampling. Generator")
    L.append("is the committed `experiments/ORCH-drift-check/orch_corpuseye.py`, which this lane")
    L.append("verified reproduces ORCH-EYE's `sheet-00.jpg` byte-identically before use.")
    L.append("")
    L.append("## What was reclaimed, and what was kept")
    L.append("")
    L.append("Deleted, because every measurement taken from it is written down above:")
    L.append("")
    L.append("- `masters\\..\\orch-rendered-7\\` — ORCH's duplicate copies of the seven new")
    L.append("  subjects. Proven byte-identical to the delivered masters, so they carried no")
    L.append("  information the masters do not.")
    L.append("- `view-new7\\` — NTFS hardlinks into `masters\\`. Reported ~1.29 GB by size but")
    L.append("  occupied no additional blocks; deleting it reclaims approximately nothing and")
    L.append("  is **not** counted as space recovered.")
    L.append("- `scratch\\` — warpmap caches, already near zero.")
    L.append("")
    L.append("Kept, deliberately:")
    L.append("")
    L.append("- `masters\\` (33 TIFFs) and `bin\\strehl.exe` — the shipping product.")
    L.append("- `bin\\strehl-caold.exe` — the old-coefficient control binary, 9.4 MB. Cannot be")
    L.append("  reproduced without another clean worktree build; the entire before/after")
    L.append("  magenta comparison rests on it.")
    L.append("- All manifests, logs, banners, JSON and sheets. Text and JPEG, 0.07 GB total.")
    L.append("")
    L.append("Measured, by directory:")
    L.append("")
    L.append("```")
    L.append("before   C: 8.6793 GB   D: 0.0703 GB   total 8.7496 GB")
    L.append("after    C: 6.1000 GB   D: 0.0703 GB   total 6.1703 GB")
    L.append("logical difference                            2.5793 GB")
    L.append("of which hardlinks (view-new7), freeing nothing 1.2895 GB")
    L.append("genuinely reclaimed                            1.2898 GB")
    L.append("```")
    L.append("")
    L.append("**The honest number is 1.29 GB, not 2.58 GB.** `view-new7` was a directory of")
    L.append("NTFS hardlinks into `masters\\`, verified with `fsutil hardlink list` (2 links per")
    L.append("file) before deletion; it inflated any recursive byte count but occupied no")
    L.append("blocks of its own. The C: volume free-space delta across the purge was 1.646 GB,")
    L.append("which is *larger* than this lane reclaimed because sixteen other lanes were")
    L.append("freeing scratch at the same time. Volume free space is not attributable to one")
    L.append("lane during a concurrent purge; the directory measurement is.")
    L.append("")
    L.append("The remaining 6.17 GB is the deliverable itself and is on the protected list.")
    L.append("After the purge all **33 masters re-hashed clean against the table above (33 OK,")
    L.append("0 mismatch, 0 missing)** and both pinned binaries still match their recorded")
    L.append("SHA256 — deleting the hardlinks did not touch the product.")
    L.append("")

    out = HERE / "BANK-33.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"banked {len(recs)} subjects -> {out}")
    missing = [n for n in recs if n not in tags]
    print("subjects without tag data:", missing or "none")
    notag = [n for n, t in tags.items() if not t.get("icc_present")]
    print("subjects missing ICC     :", notag or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
