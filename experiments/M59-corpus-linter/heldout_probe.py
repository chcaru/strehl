"""M59 pass 9: is there a valid held-out set for A4's false-positive rate?

A4's two exclusions (possessive subject, reported speech) were derived from the
only two false positives in SYNTHESIS §4, so the measured 0% is in-sample. The
orchestrator asks whether the corpus already contains material that could give
an out-of-sample estimate: report files, commit messages and OWNER-QUESTIONS.md
are all prose that mentions questions and verdicts, and none of it was read when
the exclusions were written.

This runs A4's matcher over exactly that material and classifies every candidate:

    CORROBORATED  the §10/§5 item carries the marker -- no violation
    EXCLUDED-*    one of the four exclusion rules fired
    RESIDUAL      would be reported as a violation

The residual then has to be read by hand, because the question the held-out set
can answer and the question it cannot are different (see the report's §10.2).

Read-only. Run: python experiments/M59-corpus-linter/heldout_probe.py
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corpus_lint as cl                                    # noqa: E402

PAT = cl.A4_CLAIM
NEGATION = cl.A4_NEGATION
KIND_SECTION = {"question": 10, "discipline": 5}


def held_out_sources():
    """Every prose source EXCEPT SYNTHESIS.md, which is what the rules were
    written against."""
    out = []
    research = os.path.join(ROOT, "docs", "research")
    for name in sorted(os.listdir(research)):
        rel = "docs/research/" + name
        if name.endswith(".md") and rel != cl.SYNTHESIS:
            out.append((rel, io.open(os.path.join(research, name),
                                     encoding="utf-8").read()))
    for extra in ("OWNER-QUESTIONS.md", "docs/captures-needed.md", "README.md",
                  "AGENTS.md"):
        p = os.path.join(ROOT, extra)
        if os.path.isfile(p):
            out.append((extra, io.open(p, encoding="utf-8").read()))
    crates = os.path.join(ROOT, "crates")
    for dirpath, dirnames, filenames in os.walk(crates):
        dirnames[:] = [d for d in dirnames if d != "target"]
        for name in sorted(filenames):
            if name.endswith(".rs"):
                rel = os.path.relpath(os.path.join(dirpath, name),
                                      ROOT).replace("\\", "/")
                out.append((rel, io.open(os.path.join(dirpath, name),
                                         encoding="utf-8").read()))
    p = subprocess.run(["git", "log", "--format=%h%x00%s%x00%b%x01"],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode == 0:
        blob = p.stdout.decode("utf-8", "replace")
        for entry in blob.split("\x01"):
            parts = entry.split("\x00")
            if len(parts) == 3 and parts[0].strip():
                out.append(("commit " + parts[0].strip(),
                            parts[1] + "\n" + parts[2]))
    return out


def classify(line, m, index):
    kind = m.group(1).lower()
    num = int(m.group(2))
    marker = m.group("mk").upper()
    body = index.item_body(KIND_SECTION[kind], num)
    if not body:
        return "NO-SUCH-ITEM", kind, num, marker
    if cl.a4_corroborated(body, marker):
        return "CORROBORATED", kind, num, marker
    visible = cl.STRIKETHROUGH.sub("", line)
    if m.group(0) not in visible:
        return "EXCLUDED-strikethrough", kind, num, marker
    if line[m.end(2):m.end(2) + 2] in ("'s", "\u2019s"):
        return "EXCLUDED-possessive", kind, num, marker
    quoted = [(q.start(), q.end()) for q in cl.QUOTED_SPAN.finditer(line)]
    if any(a <= m.start() < b for a, b in quoted):
        return "EXCLUDED-reported-speech", kind, num, marker
    if NEGATION.search(m.group("mid")) or \
            NEGATION.search(line[max(0, m.start() - 40):m.start()]):
        return "EXCLUDED-negation", kind, num, marker
    return "RESIDUAL", kind, num, marker


def main():
    syn = cl.Doc(ROOT, cl.SYNTHESIS)
    index = cl.Index(syn, cl.Doc(ROOT, cl.AGENTS))
    counts = {}
    residual = []
    excluded = []
    sources = held_out_sources()
    for rel, text in sources:
        for i, line in enumerate(text.replace("\r\n", "\n").split("\n")):
            bare = cl.strip_code_spans(line)
            for m in PAT.finditer(bare):
                verdict, kind, num, marker = classify(bare, m, index)
                counts[verdict] = counts.get(verdict, 0) + 1
                row = (rel, i + 1, kind, num, marker, m.group(0)[:76])
                if verdict == "RESIDUAL":
                    residual.append(row)
                elif verdict.startswith("EXCLUDED"):
                    excluded.append((verdict,) + row)

    print("held-out sources: %d (report files, OWNER-QUESTIONS, AGENTS, "
          "rust, and every commit message)" % len(sources))
    print("SYNTHESIS.md deliberately excluded -- it is the in-sample set.")
    print("")
    total = sum(counts.values())
    print("candidates matched by A4's pattern: %d" % total)
    for k in sorted(counts):
        print("   %-26s %4d" % (k, counts[k]))
    print("")
    print("EXCLUSIONS THAT FIRED OUT OF SAMPLE -- the part that is testable")
    if not excluded:
        print("   none. The exclusion rules were never exercised here, so this")
        print("   material CANNOT estimate their false-positive rate.")
    for verdict, rel, line, kind, num, marker, raw in excluded:
        print("   %-26s %s:%d" % (verdict, rel, line))
        print("      %s" % raw)
    print("")
    print("RESIDUAL -- would be reported as a violation (%d)" % len(residual))
    for rel, line, kind, num, marker, raw in residual[:40]:
        print("   %s:%d  %s %d -> %s" % (rel, line, kind, num, marker))
        print("      %s" % raw)
    if len(residual) > 40:
        print("   ... %d more" % (len(residual) - 40))


if __name__ == "__main__":
    main()
