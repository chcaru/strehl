"""Bank facts 1882-1884: the env channel's unvalidated hole, measured by ORCH."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1881 | MEASURED | V-GATHER |"

ROWS = [
    ("1882", "MEASURED", "ORCH",
     "**ON THE SHIPPING BACKEND `STREHL_SOFT_GATE` IS NOT MERELY IGNORED, IT IS UNVALIDATED: A "
     "VALUE NAMING NO KERNEL RUNS TO COMPLETION AND PRODUCES BYTE-IDENTICAL OUTPUT.** Measured on "
     "`coffee-bubbles -l 3 --srgb` through the release binary. Pyramid, the default: unset rc=0, "
     "`on` rc=0, `zzznope` rc=0, and all three outputs hash to SHA256 `C5E59BC931C3AD93E08317CF4F0"
     "657E6` at 197,801,290 bytes. Estimator with `--photometric off`: unset rc=0, `on` rc=101, "
     "`zzznope` rc=101. The estimator column is the control that proves the read path is live and "
     "the zero is a real zero rather than a dead probe; `kernel_from_setting` rejects an unnamed "
     "kernel and `Estimator::new` panics on that error at `merge.rs:1457`. So the pyramid column "
     "is not a permissive parse, it is no parse at all. This is a SHIPPED instance of the failure "
     "`strehl stack --help` claims to have eliminated, quote, a flag that parses and does nothing "
     "is indistinguishable from one that works, and this project has shipped that failure before. "
     "The FLAG channel was fixed by refusing estimator-only flags under pyramid. The ENV channel "
     "was not, and it carries 46 variables."),

    ("1883", "DISCIPLINE", "ORCH",
     "**AN EXIT CODE IS NOT A MEASUREMENT OF THE KNOB YOU SET UNLESS AN UNSET CONTROL ON THE "
     "IDENTICAL COMMAND LINE RETURNS SOMETHING ELSE.** ORCH's first soft-gate probe read rc=1 on "
     "both estimator arms and was one keystroke from the conclusion that the estimator rejects "
     "the variable too. It does not. rc=1 was an unrelated failure of photometric normalisation "
     "on that subject, quote, U3 the eroded low-detail region keeps only 0 px, which fires "
     "whatever the environment says. The var-unset control on the same command line returned the "
     "same rc=1 and exposed it; adding `--photometric off` then separated the arms cleanly into "
     "0/101/101. Same family as crediting an uncommissioned instrument's CLEAN verdicts: an "
     "outcome that had nothing to do with the question, scored as though it answered it. The "
     "cheapest defence is structural, not clever - every arm carries its own matched control, and "
     "an arm whose control already shows the effect has measured nothing."),

    ("1884", "CORRECTED", "V-REVIEW",
     "**THE RESIDUAL UNSCORED-HALO COUNT IS 11; THE COMPETING 8 AND 6 ARE BOTH VOID, RETRACTED BY "
     "THE LANE THAT PRODUCED THEM.** V-REVIEW twice pushed 6 at ORCH as a correction, then checked "
     "it against its own report and found `vh_union.py` had reached 6 by crediting `halo3` with "
     "scoring three subjects CLEAN. `halo3` FAILED ITS OWN COMMISSION, and an instrument that "
     "cannot pass its gradient arms cannot move a subject out of UNSCORED - which its own "
     "`HALO-residual.md` §7 already said in terms, quote, no instrument passed commissioning, so "
     "absence of detection is not evidence of absence. The 8 came from `halo3`'s UNSCORED column "
     "and dies the same way. Surviving accounting, from `halo_profile.py`, the only commissioned "
     "instrument: clean 11, blind 4, unmeasurable 7, summing to 26. The retracted 6 reached no "
     "report file but IS in the text of commit `c07cfc8d`, which is now wrong in the log and is "
     "being left wrong with a later retraction rather than rewritten."),
]


def build_row(num, kind, lane, body):
    if "|" in body:
        raise SystemExit(f"fact {num}: raw pipe in body")
    if body.count("*") % 2 != 0:
        raise SystemExit(f"fact {num}: odd asterisk count")
    return f"| {num} | {kind} | {lane} | {body} |\n"


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    for num, _, _, _ in ROWS:
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")

    new = [build_row(*r) for r in ROWS]
    lines[at + 1:at + 1] = new

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)

    print(f"inserted {len(new)} rows after fact 1881 (line {at + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
