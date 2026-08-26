import pathlib
p = pathlib.Path("docs/research/V-THESIS.md")
t = p.read_text(encoding="utf8")
ADD = """## The same result with no ladder, no inversion and no Gaussian model

Every defect above lives in `blureq.py`'s ladder and its inversion. So here is
the headline restated in units that need neither. `S2_f50` is a half-energy
frequency in cyc/px -- it *is* "how fine this arm resolves". The README's claim,
put in these units, is that `f50_merge / f50_argmax` should be 1.20 to 1.80.
Computed from BUILD-THESIS's own per-tile numbers (*reproduced*, not mine):

| subject | f50 merge | f50 argmax | raw ratio | geometry-corrected |
| --- | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | 0.0735 | 0.0728 | 1.010 | 1.034 |
| `bee-1-cpl` | 0.0768 | 0.0766 | 1.003 | 0.995 |
| `leaf-2-cpl` | 0.0493 | 0.0496 | 0.993 | 0.970 |
| `flowers-cpl` | 0.0654 | 0.0687 | 0.952 | 0.830 |
| `tweezers-cpl` | 0.0830 | 0.0837 | 0.992 | 0.924 |
| `flat-on-ruler-cpl` | 0.1057 | 0.1174 | 0.900 | 0.918 |

**The merge's half-energy frequency never exceeds the selector's by more than
1.0% raw or 3.4% geometry-corrected. The claim requires 20% to 80%.** Median
0.993 raw, 0.947 corrected. This is the number to publish, because no ladder,
no inversion and no blur model stands between it and the pixels.

It also closes the one gap in the dB argument above: those f50 values, 0.049 to
0.106 cyc/px, all sit inside the 0.031-0.25 cyc/px band my spectral fit covers,
so the -1.84 dB a 1.2x gain would produce would have landed where I was looking.

"""
t = t.replace("## The claim that is defensible", ADD + "## The claim that is defensible")
p.write_bytes(t.encode("utf8").replace(b"\r\n", b"\n"))
print("updated", p.stat().st_size, "bytes")
