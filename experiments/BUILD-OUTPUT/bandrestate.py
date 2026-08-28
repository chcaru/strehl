"""Re-state this lane's fine-detail claim in the band that may carry it.

ORCH's general rule, issued after he twice quoted a sharpness difference
measured in an unqualified band: no sharpness, softening or acuity claim may be
quoted without naming the band and the subject's qualification at that band.

I violated it. In commit f273e50e and in the message that accompanied it I wrote
that `--pyramid-gate 64` "destroys fine detail (grain-band structure -85.75% on
lead-1-cpl, -65.57% on 112MSDCF)". `grain` is <=3 px, >=0.33 cyc/px, and
recertlib's own BANDS table marks it `sharpness_admissible = False`; `classify`
enforces that by appending "(noise-only band; no sharpness claim admissible)" to
every grain verdict it forms. The harness refused the claim and I made it anyway
by reading the raw `d_structure` number out from under its own verdict.

The code was right and the narration was wrong, which is the more dangerous of
the two orders: nothing goes RED when a human misquotes a correctly-labelled
number. So this script re-states the claim positionally -- per band, with the
passband in cyc/px and the admissibility flag printed beside every figure, and
with the inadmissible band's structure column BLANKED rather than printed, so
the number that misled me is not available to mislead the next reader.

`struct` is 5-13 px, 0.077-0.20 cyc/px, admissible. ORCH reports the corpus
signal/noise boundary moving over 0.17-0.48 cyc/px, so struct's TOP EDGE (0.20)
can sit above the boundary on the corpus's worst subject while its bulk sits
well below; that caveat is printed rather than hidden. `mottle` is 21-61 px,
0.016-0.048 cyc/px -- a factor of 3.5 below the lowest boundary in the corpus,
which is why the mottle result is not exposed to this correction at all.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "BUILD-RECERT"))
from recertlib import BANDS  # noqa: E402

SCORES = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs\scalescore.json")
SUBJECTS = ["coffee-bubbles", "lead-1-cpl", "113MSDCF",
            "flat-on-ruler-cpl", "112MSDCF", "foam"]
ARMS = [("SC-PG64-bc6fa3c7", "--pyramid-gate 64"),
        ("SC-D4096-bc6fa3c7", "SCALE=1,1,1,4096,4096,4096")]

# ORCH: "The signal/noise boundary is a property of the subject and moves
# 0.17-0.48 cyc/px across this corpus."
BOUNDARY_LO, BOUNDARY_HI = 0.17, 0.48


def main():
    data = json.loads(SCORES.read_text(encoding="utf-8"))["per_subject"]
    print("band passbands, and whether each may carry a sharpness claim\n")
    for name, (_, px, cyc, adm) in BANDS.items():
        lo, hi = cyc
        margin = BOUNDARY_LO / hi if hi > 0 else float("inf")
        note = ("ADMISSIBLE" if adm else "NOISE ONLY -- no sharpness claim")
        rel = (f"top edge {hi} is {'ABOVE' if hi > BOUNDARY_LO else 'below'} the "
               f"corpus's lowest boundary {BOUNDARY_LO}")
        print(f"  {name:<7} {px:<8} {lo}-{hi} cyc/px  {note}")
        print(f"  {'':<7} {rel}; margin vs lowest boundary = {margin:.2f}x")
    print(f"\n  corpus signal/noise boundary spans {BOUNDARY_LO}-{BOUNDARY_HI} "
          f"cyc/px (ORCH, per-subject)\n")

    for arm, label in ARMS:
        print(f"\n{'=' * 74}\n{label}   (arm {arm})\n")
        hdr = f"  {'subject':<20}"
        for b in ("mottle", "struct", "grain"):
            hdr += f"{b + ' dStruct':>17}"
        print(hdr)
        for s in SUBJECTS:
            row = f"  {s:<20}"
            for b in ("mottle", "struct", "grain"):
                adm = BANDS[b][3]
                v = data.get(arm, {}).get(s, {}).get(b, {}).get("median_d_structure")
                if not adm:
                    # Blanked deliberately. This is the number I misquoted; a
                    # value that may not support the claim should not be sitting
                    # in the column a reader scans for that claim.
                    row += f"{'[inadmissible]':>17}"
                elif v is None:
                    row += f"{'--':>17}"
                else:
                    row += f"{v:>+17.4f}"
            print(row)

    print(f"\n{'=' * 74}")
    print("The claim, re-stated in the band that may carry it:")
    st = data["SC-PG64-bc6fa3c7"]
    worst = sorted(SUBJECTS,
                   key=lambda s: st[s]["struct"]["median_d_structure"])[:2]
    for s in worst:
        v = st[s]["struct"]["median_d_structure"]
        print(f"  --pyramid-gate 64 costs {-v * 100:5.2f}% of struct-band "
              f"structure on {s}  (5-13 px, 0.077-0.20 cyc/px, admissible)")
    d4 = data["SC-D4096-bc6fa3c7"]
    lo = min(d4[s]["struct"]["median_d_structure"] for s in SUBJECTS)
    hi = max(d4[s]["struct"]["median_d_structure"] for s in SUBJECTS)
    print(f"  the per-band 4096x arm moves struct-band structure by "
          f"{lo:+.4f} to {hi:+.4f} over the same six subjects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
