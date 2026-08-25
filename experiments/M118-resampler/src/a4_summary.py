"""M118 arm 6 -- consolidate every published number into one dump.

No figure in the report is transcribed from notes: this writes the tables the
report quotes, so a reader can diff the two. Same discipline as
`experiments/M95-kernel/out/k6_dump.txt`.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent.parent
ARMS = ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"]
SUBJECTS = ["bee-3-cpl", "wrapped-text-1", "flat-on-ruler-cpl"]

lines = []
def p(s=""):
    lines.append(s)
    print(s)

ds = json.loads((HERE / "out" / "a2_datasheet.json").read_text())
pred = ds["prediction"]

p("M118 CONSOLIDATED DUMP")
p("SHA 4beac7300e318f6f0aaf10b6a88e57f311b9e814, gate 4, full stacks, sidecar-override")
p("")
p("== T1. Band gain vs catmull-rom (dex). M1 = detail decile, M2 = flat decile.")
p("")
p(f"{'subject':<19}{'arm':<13}{'pred':>8}{'M1':>9}{'M2':>9}{'M3':>9}{'flat sd':>10}"
  f"{'extrema':>9}{'n_eff':>7}{'secs':>8}")
for s in SUBJECTS:
    a1 = json.loads((HERE / "out" / f"a1_{s}.json").read_text())
    for a in ARMS:
        r = a1["arms"][a]
        p(f"{s:<19}{a:<13}{pred[a]:+8.4f}{r['M1_detail_dex']:+9.4f}{r['M2_flat_dex']:+9.4f}"
          f"{r['M3_discrimination_dex']:+9.4f}{r['M4_flat_sd_DN']:10.1f}"
          f"{r['M5_ratio_vs_cr']:9.4f}{float(r['mean_n_eff']):7.2f}{r['secs']:8.1f}")
    p("")

p("== T2. Stratum separation and rule-9 verdict (B3)")
p("")
p(f"{'subject':<19}{'detail grad':>12}{'flat grad':>11}{'sep':>7}   rule-9 on lanczos3")
for s in SUBJECTS:
    a1 = json.loads((HERE / "out" / f"a1_{s}.json").read_text())
    l3 = a1["arms"]["lanczos3"]
    verdict = ("FAILS -- M2 >= M1, the gain is not concentrated in detail"
               if l3["M2_flat_dex"] >= l3["M1_detail_dex"] else "passes")
    p(f"{s:<19}{a1['grad_detail']:12.1f}{a1['grad_flat']:11.1f}"
      f"{a1['grad_detail']/a1['grad_flat']:7.2f}   {verdict}")
p("")

p("== T3. ORCH N4 -- election-agreement stratification, lanczos3")
p("")
p(f"{'subject':<19}{'agree%':>8}{'hi':>9}{'lo':>9}{'delta':>9}{'corr':>9}{'% of effect':>13}  N4")
for s in SUBJECTS:
    n4 = json.loads((HERE / "out" / f"a3_n4_{s}.json").read_text())["arms"]["lanczos3"]
    p(f"{s:<19}{100*n4['agree_whole']:8.2f}{n4['median_split_hi']:+9.4f}"
      f"{n4['median_split_lo']:+9.4f}{n4['median_delta']:+9.4f}{n4['corr']:+9.4f}"
      f"{100*n4['reversal_frac_of_effect']:13.1f}  "
      f"{'REVERSED' if n4['N4_reversed'] else 'not reversed'}")
p("")

p("== T4. The datasheet test -- how much do the photographs move the answer?")
p("")
rows = [r for r in ds["rows"] if r["arm"] != "catmull-rom"]
err = [r["abs_err"] for r in rows]
eff = [abs(r["pred"]) for r in rows]
p(f"  cells (3 subjects x 4 non-baseline arms) : {len(rows)}")
p(f"  mean |measured - predicted|              : {sum(err)/len(err):.4f} dex")
p(f"  max  |measured - predicted|              : {max(err):.4f} dex")
p(f"  mean |predicted effect|                  : {sum(eff)/len(eff):.4f} dex")
p(f"  photographs move the answer by           : {100*(sum(err)/len(err))/(sum(eff)/len(eff)):.1f}%")
p("")
p("  per-arm spread of the MEASURED gain across the three subjects:")
for a in ARMS:
    if a == "catmull-rom":
        continue
    v = [r["M1"] for r in ds["rows"] if r["arm"] == a]
    p(f"    {a:<12} {min(v):+.4f} .. {max(v):+.4f}   range {max(v)-min(v):.4f} dex   "
      f"predicted {pred[a]:+.4f}")
p("")

p("== T5. Nulls, plants and the poisoning check")
p("")
for s in SUBJECTS:
    r1 = json.loads((HERE / "out" / f"r1_{s}.json").read_text())
    a1 = json.loads((HERE / "out" / f"a1_{s}.json").read_text())
    p(f"  {s}")
    p(f"    B5 null + B7 poisoning (catmull-rom cold, re-run after every other arm): "
      f"{'BYTE-IDENTICAL' if r1['null_pass'] else 'DIFFERS -- FAIL'}")
    p(f"    B6 P1 wiring plant  : {r1['plant_P1_distinct_hashes']}/5 distinct hashes")
    p(f"    B6 P2 metric plant  : blur sigma 0.5 -> {a1['plant_P2']['blur_sigma0.5']:+.4f} dex, "
      f"unsharp x1.5 -> {a1['plant_P2']['unsharp_x1.5']:+.4f} dex  "
      f"({'pass' if a1['plant_P2_pass'] else 'FAIL'})")
    p(f"    pinned viewing exposure: {a1['pinned_exposure']}")
p("")

p("== T6. Cost, as a BOUND (shared machine, 3 other strehl processes live; rule 16)")
p("")
for s in SUBJECTS:
    a1 = json.loads((HERE / "out" / f"a1_{s}.json").read_text())
    cr = a1["arms"]["catmull-rom"]["secs"]
    row = "  ".join(f"{a}={a1['arms'][a]['secs']/cr:.2f}x" for a in ARMS)
    p(f"  {s:<19} catmull-rom = {cr:6.1f}s   {row}")

(HERE / "out" / "dump.txt").write_text("\n".join(lines), encoding="utf-8")
