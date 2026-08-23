"""M60b/36 -- verify every headline number in Part II against its data file.

Discipline 351: do not trust that a number was transcribed correctly; read it
back out of the artefact that produced it.  Each row below is (token, file).
Failure prints the token and exits non-zero -- but the exit code is not the
evidence, the printed report is.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
REPORT = HERE.parents[2] / "docs" / "research" / "M60-bimodality.md"

# (token as written in the report, data file it is cited from)
CHECKS = [
    # T1 / T2 / T3 -- 31-swap.txt
    ("0.19x", "31-swap.txt"), ("1.21x", "31-swap.txt"), ("0.70x", "31-swap.txt"),
    ("1.97%", "31-swap.txt"), ("10.61%", "31-swap.txt"),
    ("43.10%", "31-swap.txt"), ("35.66%", "31-swap.txt"),
    ("4.92%", "31-swap.txt"), ("7.06%", "31-swap.txt"),
    ("108.412", "31-swap.txt"), ("27.503", "31-swap.txt"), ("3.942", "31-swap.txt"),
    ("7.600", "31-swap.txt"), ("6.594", "31-swap.txt"),
    ("2.477", "31-swap.txt"), ("2.357", "31-swap.txt"),
    ("1.067", "31-swap.txt"),
    ("10133", "31-swap.txt"), ("994940", "31-swap.txt"),
    ("6.91", "31-swap.txt"), ("27.16", "31-swap.txt"),
    ("13.79", "31-swap.txt"), ("43.52", "31-swap.txt"),
    ("22.05", "31-swap.txt"), ("55.29", "31-swap.txt"),
    ("31.30", "31-swap.txt"), ("64.28", "31-swap.txt"),
    ("43.53", "31-swap.txt"), ("71.39", "31-swap.txt"),
    ("70.4", "31-swap.txt"),
    # S1 repair / T4 / T5 -- 32-swap2.txt
    ("0.82x", "32-swap2.txt"), ("1.26", "32-swap2.txt"),
    ("17.4", "32-swap2.txt"), ("21.3", "32-swap2.txt"), ("80.4", "32-swap2.txt"),
    ("41.1", "32-swap2.txt"), ("14.7", "32-swap2.txt"), ("64.4", "32-swap2.txt"),
    ("14.0", "32-swap2.txt"), ("12.5", "32-swap2.txt"), ("92.6", "32-swap2.txt"),
    ("85.2", "32-swap2.txt"), ("55.3", "32-swap2.txt"), ("41.2", "32-swap2.txt"),
    ("17.2", "32-swap2.txt"), ("31.6", "32-swap2.txt"), ("39.4", "32-swap2.txt"),
    ("45.9", "32-swap2.txt"), ("48.5", "32-swap2.txt"),
    # T6 -- 33-t6.txt
    ("218.0", "33-t6.txt"), ("1.23x", "33-t6.txt"), ("0.86x", "33-t6.txt"),
    ("1.11x", "33-t6.txt"), ("1.258", "33-t6.txt"), ("4.62x", "33-t6.txt"),
    ("0.90x", "33-t6.txt"), ("0.32x", "33-t6.txt"),
    ("128406", "33-t6.txt"), ("625289", "33-t6.txt"),
    ("5.99", "33-t6.txt"), ("6.98", "33-t6.txt"),
    ("46.85", "33-t6.txt"), ("42.17", "33-t6.txt"),
    # T7 -- 34-t7.txt
    ("47.8%", "34-t7.txt"), ("26.3%", "34-t7.txt"), ("30.0%", "34-t7.txt"),
    ("29.4%", "34-t7.txt"), ("1.82x", "34-t7.txt"), ("1.59x", "34-t7.txt"),
    ("4095", "34-t7.txt"), ("329157", "34-t7.txt"), ("10041", "34-t7.txt"),
    ("105565", "34-t7.txt"), ("28.5%", "34-t7.txt"), ("23.8%", "34-t7.txt"),
    ("20.6%", "34-t7.txt"), ("11.1%", "34-t7.txt"), ("67.4%", "34-t7.txt"),
    ("11.8", "34-t7.txt"), ("10.5", "34-t7.txt"), ("11.3", "34-t7.txt"),
    # mechanism -- 35-mechanism.txt
    ("3.042", "35-mechanism.txt"), ("2.803", "35-mechanism.txt"),
    ("0.331", "35-mechanism.txt"), ("0.355", "35-mechanism.txt"),
    ("4.336", "35-mechanism.txt"), ("1.100", "35-mechanism.txt"),
    ("0.076", "35-mechanism.txt"), ("0.323", "35-mechanism.txt"),
    ("0.702", "35-mechanism.txt"), ("2.548", "35-mechanism.txt"),
    ("5.08", "35-mechanism.txt"), ("5.24", "35-mechanism.txt"),
    ("46.18", "35-mechanism.txt"), ("64.89", "35-mechanism.txt"),
    ("0.71x", "35-mechanism.txt"), ("3.63", "35-mechanism.txt"),
    ("9.2x", "35-mechanism.txt"),
    # corpus rename / matched-scene pair (added after the owner's 2026-08-23 note)
    ("0.9562", "03-previews.txt"), ("0.3834", "03-previews.txt"),
    ("0.6036", "03-previews.txt"),
    ("299", "01-survey.csv"), ("130", "01-survey.csv"), ("120", "01-survey.csv"),
    ("0.5000", "01-survey.txt"), ("0.0500", "01-survey.txt"),
    ("0.2000", "01-survey.txt"), ("0.0667", "01-survey.txt"),
    ("0.0250", "01-survey.txt"),
]


def main() -> int:
    report = REPORT.read_text(encoding="utf-8")
    # the report uses thin/no-break spaces as thousands separators; the data
    # files do not.  Compare on a digit-joined form so 994 940 matches 994940.
    flat = re.sub(r"(?<=\d)[\s\u00a0\u2009,](?=\d)", "", report)
    cache = {}
    bad_data, bad_report = [], []
    for tok, fn in CHECKS:
        if fn not in cache:
            p = DATA / fn
            if not p.exists():
                print(f"MISSING DATA FILE {fn}")
                return 2
            cache[fn] = p.read_text(encoding="utf-8")
        # the report writes 'x' where the data file may write 'x' too; compare bare
        bare = tok.rstrip("%x")
        if bare not in cache[fn]:
            bad_data.append((tok, fn))
        if bare not in flat:
            bad_report.append((tok, fn))

    print(f"M60b/36 -- read-back of Part II numbers")
    print(f"  report   {REPORT.name}  {len(report)} chars")
    print(f"  checked  {len(CHECKS)} tokens across {len(cache)} data files")
    if bad_data:
        print(f"  NOT FOUND IN DATA ({len(bad_data)}):")
        for tok, fn in bad_data:
            print(f"    {tok!r} not in {fn}")
    if bad_report:
        print(f"  NOT FOUND IN REPORT ({len(bad_report)}):")
        for tok, fn in bad_report:
            print(f"    {tok!r} (from {fn})")
    if not bad_data and not bad_report:
        print("  ALL TOKENS PRESENT IN BOTH THE DATA FILE AND THE REPORT")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
