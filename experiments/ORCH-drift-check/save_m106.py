"""Save M106-freeze's verifier report to the corpus verbatim.

The verifier's instructions bar it from writing findings to disk, so the
orchestrator persists them. The report is reproduced as delivered, with only
a provenance header added -- no editing of its claims, its numbers, or its
self-disclosed gaps.
"""
import io
import os
import re

SRC = r"C:\Users\chris\AppData\Local\Temp\1787591606990-copilot-tool-output-20f8bbbbdcd54a458e867325213331d1.txt"
DST = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M106-freeze-attribution.md"

HEADER = """# M106 -- attributing the broken byte-freeze

**Author:** `ultracode:ultra-verifier` agent `a7cf3e3e`, 6764 s, 3 turns, claude-opus-5.
**Persisted by:** the orchestrator, verbatim. The verifier's brief bars it from
writing findings to disk, so this file is a transcription rather than a rewrite.
**Nothing below has been edited** -- not the claims, not the numbers, not the
self-disclosed gaps. Where the orchestrator disagrees or has acted since, that is
recorded in `SYNTHESIS.md` against the fact numbers, not here.

**Read the verdict first: the defect this milestone was commissioned to attribute
did not happen.** The dispatch that commissioned it -- written by the orchestrator
-- compared a `--gate 2` render against a baseline rendered at the default gate
4.0, and read the difference as a broken freeze. A different, real break was found
in the course of refuting the reported one.

---

"""


def main():
    with io.open(SRC, encoding="utf-8", errors="replace") as f:
        text = f.read()

    start = text.index("[Turn 0]")
    body = text[start + len("[Turn 0]"):]
    end = body.find("\n[Turn 1]")
    assert end > 0, "could not find the end of turn 0"
    body = body[:end].strip()

    # sanity: the verdict and the attributed commit must both be present, or
    # the extraction window is wrong.
    for probe in ("DEFECTS FOUND", "885e9f7", "41974F2A", "54A5E20F"):
        assert probe in body, f"extraction lost {probe!r}; window is wrong"

    n_pipe_rows = len([l for l in body.split("\n") if l.startswith("|")])
    print(f"extracted {len(body)} chars, {len(body.splitlines())} lines, "
          f"{n_pipe_rows} table rows")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with io.open(DST, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER + body + "\n")
    print("wrote", DST)


if __name__ == "__main__":
    main()
