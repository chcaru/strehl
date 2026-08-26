from pathlib import Path

P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")

OLD = """| path | what it shows |
| --- | --- |
| `pics/merge-vs-frame52.png` | The whole finding in one frame. Same crop, same linear stretch, no gamma: the merged output has a dark band, a bright band and a second dark band; the in-focus single frame has a clean step onto flat backdrop. |
| `pics/coffee-bean-ring.png` | The ring hugging a smooth silhouette, with the registered ray profiles beside it. |
| `pics/mask-disagreement.png` | Why attack 4 landed against me. ORCH's mask is tight to the bean; mine swallows the dim corner of the sweep. |
"""

NEW = r"""`*.png` is gitignored repo-wide, so these live in scratch, under
`C:\dev\strehl-out\V-RIM\pics\`.

| file | what it shows |
| --- | --- |
| `fb-merge-vs-frame110.png` | **Look at this one first.** `flower-bud-alone-cpl`, same crop, same linear stretch, no gamma. The in-focus frame is flat at 19100 DN right up to the silhouette. The merge sags to 13800 DN over the 280 px approaching it, with an overshoot spike at the edge. Nothing in the photograph produced that trough. |
| `merge-vs-frame52.png` | The same comparison on `coffee-bean`: the merged output has a dark band, a bright band and a second dark band; the in-focus single frame has a clean step onto flat backdrop. |
| `coffee-bean-ring.png` | The ring hugging a smooth silhouette, with the registered ray profiles beside it. This is the frame that refutes C2. |
| `mask-disagreement.png` | Why attack 4 landed against me. ORCH's mask is tight to the bean; mine swallows the dim corner of the sweep. |
"""

assert OLD in t, "ANCHOR NOT FOUND"
t = t.replace(OLD, NEW)

O2 = "Picture: `pics/merge-vs-frame52.png`."
N2 = ("Pictures: `fb-merge-vs-frame110.png` and `merge-vs-frame52.png`; see the\n"
      "Pictures table for the directory.")
assert O2 in t, "ANCHOR 2 NOT FOUND"
t = t.replace(O2, N2)

P.write_text(t, encoding="utf-8", newline="\n")
print("written, lines:", t.count("\n") + 1)
