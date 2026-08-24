"""Repair the M99 ledger row: the table is stem | task | writes to | state."""
import io
import re

P = "AGENTS.md"
L = io.open(P, encoding="utf-8").read().split("\n")
i = next(i for i, l in enumerate(L) if l.startswith("| `M99` |"))
cells = L[i].split("|")
assert len(cells) == 5, "expected the broken 3-column row, got %d cells" % len(cells)

writes = (" `docs/research/M99-photometric.md`, "
          "`crates/strehl-core/src/photometric.rs`, "
          "`crates/strehl-cli/examples/`, `experiments/M99-photometric/`, "
          "`C:\\dev\\strehl-out\\M99\\` ")
fixed = "|".join([cells[0], cells[1], cells[2], writes, cells[3], cells[4]])

n = len(re.findall(r"(?<!\\)\|", fixed))
assert n == 5, "repaired row has %d unescaped pipes, need 5 for 4 columns" % n
L[i] = fixed
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("repaired M99 row at line %d -> %d cells" % (i, len(fixed.split('|'))))
