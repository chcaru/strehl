"""Append section 32 and repair section 31.1's provenance block.

Two things, both prompted by the orchestrator's sidecar quarantine and the
M106 freeze attribution:

1. 31.1 recorded its hash beside the words "the shipped default gate". That
   is the exact defect M106 cost 1.9 hours to: three milestones froze three
   invocations, none recorded the command, and splicing one's flag onto
   another's produced a fourth nobody had frozen. My own most recent hash had
   the same hole. It now carries the full invocation and the resolved gate
   with its source.
2. Section 32 records the audit of both hazards against M87, by measurement.

Writes CRLF, validates every fact row, and refuses to write if any C0 control
character would enter the file.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
BIN = pathlib.Path(r"C:\dev\strehl-out\M87-bee\bin\strehl-m87.exe")

z = json.loads((DATA / "51-zoomnull.json").read_text(encoding="utf-8"))
un, al = z["ZOOMNULL"]["before"], z["ALIGNED"]["before"]
share = 100.0 * (un - al) / un
d_un, d_al, ratio = z["ZOOMNULL"]["delta_pct"], z["ALIGNED"]["delta_pct"], z["ratio"]

h = hashlib.sha256(BIN.read_bytes()).hexdigest()[:24]
audit = {
    "watershed": "2026-08-24T03:15:23-07:00",
    "watershed_commit": "885e9f7",
    "pre_align_data_files": 27,
    "align_share_of_halo_pct": share,
    "unaligned_delta_pct": d_un,
    "aligned_delta_pct": d_al,
    "ratio": ratio,
    "limit_flags_in_m87": 0,
    "binary_sha24": h,
    "default_gate": 4.0,
}
(DATA / "93-audit.json").write_text(json.dumps(audit, indent=1), encoding="utf-8")

s = DOC.read_bytes().decode("utf-8")
assert s.count("\n") == s.count("\r\n"), "not pure CRLF"

# ---- 1. repair 31.1's provenance block -------------------------------
anchor = ("alignment      : ON (sidecar-override), reference frame 149, "
          "299 placed / 0 refused")
assert s.count(anchor) == 1, "MUTATION TARGET NOT FOUND: 31.1 alignment line"
inv = (
    "strehl stack D:\\personal\\macro\\bee-3-cpl --srgb --auto-exposure \\\r\n"
    "    --index-map ... --n-eff-map ...        # no --gate flag was passed\r\n"
    "gate           : 4.0  (resolved DEFAULT_GATE, `merge.rs:297`; recorded\r\n"
    "                 explicitly because a default is not a record --\r\n"
    "                 `byte-freeze.rs:855` notes it \u201cwas not always\u201d 4.0)\r\n"
    "binary         : sha256 " + h + "  (frozen into my own scratch)\r\n"
)
s = s.replace(anchor, inv + anchor)

# ---- 2. fact rows ----------------------------------------------------
rows = [
    ("P124", "**No M87 render could have taken the 40-frame `bee-3-cpl` "
     "sidecar, because M87 never passed `--limit`.** The quarantined file "
     "(1560 bytes, a 40-frame solve for a 299-frame bracket) is rejected by "
     "`load_or_solve`'s frame-count guard on every full-bracket run. `--limit` "
     "appears **0** times across all 30 M87 scripts.",
     "The hazard the orchestrator described is real but needs a `--limit N` "
     "run that meets a sidecar of exactly N frames. M87 rendered full "
     "brackets only, so the guard fires rather than the trap. \u00a730 "
     "separately closed the one render that was exposed to the *align* "
     "default, by hash equality rather than by argument."),
    ("P125", "**The M86c alignment watershed moves 100% of the render's "
     "pixels but only 6.86% of the halo.** Unregistered ISO **0.06878** "
     "against aligned **0.06406** on `ROI_LEG`. The correction removes "
     "**82.76%** unaligned and **72.93%** aligned, ratio **1.135**.",
     "27 of M87's data files were written before `885e9f7` (2026-08-24 "
     "03:15:23) and so describe an unaligned merge. This bounds what that "
     "can have cost: the halo survives registration almost intact, which is "
     "why no pre-watershed verdict in this milestone changes. It is also the "
     "same operand pair as `P48`, read here for a different question."),
    ("P126", "**A hash recorded beside the words \u201cthe shipped default\u201d "
     "is not a record.** \u00a731.1's provenance block named the gate only in "
     "prose; it now carries the invocation, the resolved `DEFAULT_GATE` = "
     "**4.0** with its source, and the binary's SHA-256.",
     "M106 spent 1.9 hours attributing a regression that had not happened, "
     "because three milestones froze three different invocations and none "
     "recorded the command. `byte-freeze.rs:855` already says `DEFAULT_GATE` "
     "\u201cis 4.0 today and was not always\u201d. My own most recent hash had "
     "the identical hole, written hours after I had read the warning."),
]
tail = "| MEASURED |"
first = "| P118 |"
i = s.index(first)
j = s.index("\r\n", s.index(tail, s.index("| P123 |")))
built = []
for fid, claim, why in rows:
    row = f"| {fid} | {claim} | {why} | MEASURED |"
    assert len(__import__("re").findall(r"(?<!\\)\|", row)) == 5, f"{fid} pipes"
    assert row.count("`") % 2 == 0, f"{fid} backticks"
    assert not any(ord(c) < 0x20 for c in row), f"{fid} C0"
    built.append(row)
s = s[:j] + "\r\n" + "\r\n".join(built) + s[j:]

# ---- 3. section 32 ---------------------------------------------------
sec = f"""

## 32. Two hazards audited against this milestone

The orchestrator quarantined 11 stray sidecars out of the capture library and
filed M106's attribution of the alignment watershed, and asked whether either
re-scopes numbers I have reported. Neither does, and both answers are
measurements rather than reassurances.

### 32.1 The 40-frame sidecar could not have reached M87

`bee-3-cpl\\warpmap.txt` held a **40-frame** solve for a **299-frame**
bracket. The trap is not that guard failing \u2014 it works \u2014 but that a
`--limit 40` run meets a 40-frame sidecar and accepts a solve made from a
different subset at a different reference.

**M87 never passed `--limit`.** Zero occurrences across all 30 scripts, so
every render here met the guard rather than the trap: on a full bracket the
frame count disagrees, `load_or_solve` re-solves, and the stale file is
refused. \u00a730 separately retook the one render exposed to the *align*
default and found it byte-identical to a pinned-sidecar render, 0 DN, which
settled that by hash rather than by argument (`P124`).

I hold no claim that needs retaking on this account.

### 32.2 The watershed moves every pixel and 6.86% of the halo

`885e9f7` at 2026-08-24 03:15:23 moves 100.0000% of pixels at RMS 3594 DN.
**27 of M87's data files predate it**, written between 00:13 and 03:00, and
they include the metric's own definition and the \u221228.2% unmix. So the
question is fair, and it has an operand already on the table.

`51-zoomnull.json` renders `ROI_LEG` both ways on the same binary:

| arm | halo ISO before | correction removes |
| --- | --- | --- |
| unregistered (`STREHL_ALIGN=0`) | **{un:.5f}** | **{d_un:.2f}%** |
| aligned (shipped default) | **{al:.5f}** | **{d_al:.2f}%** |

Alignment removes **{share:.2f}%** of the halo. The artifact is {100 - share:.1f}% intact
without registration, and the correction's benefit agrees across the two to a
ratio of **{ratio:.3f}**, inside the \u00b133% band I registered. A number
measured on an unaligned merge and a number measured on an aligned one are
therefore in the same magnitude class for every halo quantity M87 reports,
which is why no pre-watershed verdict here flips (`P125`).

That is a bound, not an identity. It says the watershed cannot have
manufactured or hidden this artifact; it does not license quoting a
pre-watershed figure to three decimal places against a post-watershed one.
Where \u00a731 needed precision it re-rendered rather than reached back.

### 32.3 My own hash had the defect M106 paid for

The orchestrator asked that every recorded hash carry its entire invocation,
explicitly including `--gate` even when it is the default. \u00a731.1 \u2014
written hours after I had read the sidecar warnings \u2014 recorded its
SHA-256 beside the words \u201cat the shipped default\u201d and nothing more.
That is precisely the record M106 could not use: `byte-freeze.rs:855` already
states `DEFAULT_GATE` \u201cis 4.0 today and was not always\u201d.

Repaired in place. \u00a731.1 now carries the command, `gate 4.0` with
`merge.rs:297` beside it, and the binary's SHA-256 (`P126`).

The general form, and the reason it keeps recurring: **a default is a value
that is resolved elsewhere and may move, so naming it by reference records
the resolution rather than the value.** \u201cThe shipped default\u201d is a
pointer. A byte-freeze is a claim about bytes, and a pointer does not pin
bytes.

### 32.4 Verification

`verify_s32.py` re-derives every figure here from `51-zoomnull.json` and
`93-audit.json`, re-hashes the frozen binary, and re-counts `--limit` across
the M87 script tree rather than trusting the recorded zero.
"""
s = s.rstrip("\r\n") + sec.replace("\n", "\r\n") + "\r\n"

bad = [hex(ord(c)) for c in s if ord(c) < 0x20 and c not in "\r\n"]
assert not bad, f"C0 control characters: {bad[:5]}"
assert s.count("\n") == s.count("\r\n"), "line endings damaged"
DOC.write_bytes(s.encode("utf-8"))
print(f"inserted 3 fact rows; align share {share:.4f}%; binary {h}")
print(f"wrote {DOC}: {len(s.splitlines())} lines")
