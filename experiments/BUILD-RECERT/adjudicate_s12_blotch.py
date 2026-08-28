"""Adjudicate the two section-12 blotch cells the repaired verifier flagged.

The repaired verify_s12.py reads the document's blotch(corr) cell for 109MSDCF
as 0.9683 and 119MSDCF as 0.9653, while gainbias.json holds different values.
Before correcting the document I have to establish WHICH side is wrong, and the
row itself can decide it: bought%, spent% and the exchange rate are DERIVED from
blotch_corr and sharp, and those three cells already verify GREEN against the
JSON. If the document's own derived cells agree with the JSON's blotch_corr and
disagree with the document's blotch_corr, the blotch cell is a transcription
error and the rest of the row is sound.
"""
import json
from pathlib import Path

LOGS = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs")
DOC_BLOTCH = {"109MSDCF": 0.9683, "119MSDCF": 0.9653}
DOC_BOUGHT = {"109MSDCF": "3.2", "119MSDCF": "3.8"}
DOC_RATE = {"109MSDCF": "6.71", "119MSDCF": "5.79"}

g = {r["subject"]: r for r in
     json.loads((LOGS / "gainbias.json").read_text(encoding="utf-8"))}

for s in ("109MSDCF", "119MSDCF"):
    r = g[s]
    b, sh = r["blotch_corr"], r["sharp"]
    spent = (1 - sh) * 100
    print(f"{s}")
    print(f"  JSON  blotch_corr = {b:.6f}   sharp = {sh:.6f}")
    print(f"  DOC   blotch_corr = {DOC_BLOTCH[s]:.4f}")
    for label, bl in (("JSON", b), ("DOC ", DOC_BLOTCH[s])):
        bought = (1 - bl) * 100
        rate = spent / bought
        okb = "MATCHES" if f"{bought:.1f}" == DOC_BOUGHT[s] else "conflicts with"
        okr = "MATCHES" if f"{rate:.2f}" == DOC_RATE[s] else "conflicts with"
        print(f"    from {label} blotch: bought% = {bought:.1f} ({okb} doc "
              f"{DOC_BOUGHT[s]}), rate = {rate:.2f} ({okr} doc {DOC_RATE[s]})")
    print()
