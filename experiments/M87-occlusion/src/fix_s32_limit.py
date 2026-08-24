"""Repair section 32.1 and P124, which my own verifier refuted.

I wrote that `--limit` "appears 0 times across all 30 M87 scripts" and rested
P124 on that. Two things were wrong, and the second is the substantive one:

 * there are 104 scripts, not 30; and
 * NONE of them invokes the binary. Every render in this milestone was
   hand-run from PowerShell, so a count over the Python tree is not evidence
   about renders at all. It was a true sentence about the wrong population.

The real evidence was already in the record and is stronger: the `alignment:`
line prints the placed count, and a `--limit 40` run cannot print 299.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "M87-occlusion.md"
SRC = pathlib.Path(__file__).resolve().parent
DATA = SRC.parent / "data"

scripts = sorted(SRC.glob("*.py"))
prose = {"append", "verify", "control", "fix"}
measure = [p for p in scripts if p.name.split("_")[0] not in prose
           and not p.name.startswith(("append", "verify", "control", "fix"))]
lim = [p.name for p in measure
       if re.search(r"--limit\b", p.read_text(encoding="utf-8"))]
render = [p for p in measure
          if "subprocess" in p.read_text(encoding="utf-8")
          and re.search(r"strehl[-\w]*\.exe", p.read_text(encoding="utf-8"))]
assert not lim, f"--limit present in measurement scripts: {lim}"

a = json.loads((DATA / "93-audit.json").read_text(encoding="utf-8"))
a.update({"scripts_total": len(scripts), "scripts_measurement": len(measure),
          "scripts_invoking_binary": len(render), "limit_flags_in_m87": 0})
(DATA / "93-audit.json").write_text(json.dumps(a, indent=1), encoding="utf-8")

s = DOC.read_bytes().decode("utf-8")
assert s.count("\n") == s.count("\r\n"), "not pure CRLF"

body = f"""### 32.1 The 40-frame sidecar could not have reached M87

`bee-3-cpl\\warpmap.txt` held a **40-frame** solve for a **299-frame**
bracket. The trap is not that guard failing \u2014 it works \u2014 but that a
`--limit 40` run meets a 40-frame sidecar and accepts a solve made from a
different subset at a different reference. So the question is whether any M87
render was short-bracketed.

**The recorded `alignment:` lines answer it directly.** That line prints the
placed count, and a `--limit 40` run cannot print 299. Every render in this
milestone whose provenance I kept prints a full bracket \u2014 \u00a730.2's
arm A2 and \u00a731.1's figure render both read `299 placed / 0 refused`. For
those renders the stale sidecar demonstrably did not apply, whatever was
sitting in the library at the time.

For the renders where I kept no provenance line, the argument is the guard
rather than a record: a full-bracket invocation meets a 40-frame sidecar,
the frame count disagrees, `load_or_solve` re-solves, and the stale file is
refused. The trap needs `--limit N` to meet a sidecar of exactly N frames,
and `--limit` appears **0** times in the {len(measure)} measurement scripts
here. \u00a730 separately retook the one render exposed to the *align*
default and found it byte-identical to a pinned-sidecar render, 0 DN, which
settled that one by hash rather than by argument (`P124`).

I hold no claim that needs retaking on this account.

**A correction to my own first draft of this section,** because it is the
kind that reads as evidence and is not. I first wrote that `--limit` "appears
0 times across all 30 M87 scripts" and rested the finding on it. There are
**{len(scripts)}** scripts, not 30 \u2014 and, more to the point,
**{len(render)}** of them invoke the binary. Every render here was hand-run
from PowerShell, so a count over the Python tree is a true statement about a
population that does not contain the thing being claimed. My own verifier
caught it by re-counting from disk instead of reading the number I had
recorded, which is the entire reason it re-counts.
"""
i, j = s.index("### 32.1"), s.index("### 32.2")
s = s[:i] + body.replace("\n", "\r\n") + s[j:]

row = ("| P124 | **No M87 render took the 40-frame `bee-3-cpl` sidecar: every "
       "render with recorded provenance placed the full 299-frame bracket.** "
       "The quarantined file (1560 bytes, a 40-frame solve) is refused by "
       "`load_or_solve`'s frame-count guard on any full-bracket run; the trap "
       "needs `--limit N` meeting an N-frame sidecar, and `--limit` appears "
       f"**0** times in M87's {len(measure)} measurement scripts. | The "
       "evidence is the `alignment:` placed count, not the script tree: "
       f"**{len(render)}** of {len(scripts)} scripts invoke the binary, so "
       "every render was hand-run and a flag count over the Python tree "
       "cannot speak to renders. My first draft rested on exactly that "
       "mistake and the verifier refused it. | MEASURED |")
n = len(re.findall(r"(?<!\\)\|", row))
assert n == 5, f"P124 has {n} unescaped pipes"
assert row.count("`") % 2 == 0, "P124 unbalanced backticks"
old = [l for l in s.split("\r\n") if l.startswith("| P124 |")]
assert len(old) == 1, f"MUTATION TARGET NOT FOUND: {len(old)} P124 rows"
s = s.replace(old[0], row)

bad = [hex(ord(c)) for c in s if ord(c) < 0x20 and c not in "\r\n"]
assert not bad, f"C0 control characters: {bad[:5]}"
assert s.count("\n") == s.count("\r\n"), "line endings damaged"
DOC.write_bytes(s.encode("utf-8"))
print(f"scripts {len(scripts)} measurement {len(measure)} "
      f"invoking-binary {len(render)} limit {len(lim)}")
print(f"wrote {DOC}: {len(s.splitlines())} lines")
