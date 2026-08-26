"""Back-fill the binary's verbatim self-report into already-delivered sidecars.

WHY THIS EXISTS
---------------
`finalpass.ps1` used to capture the binary's banner through a whitelist of six
keys.  Measured on a real run: the binary printed 27 settings and the whitelist
kept 6.  Among the 21 dropped were

    alignment       : ON (sidecar), reference frame 2, 4 placed / 0 refused
      held-out err  : NOT MEASURED   resampler: CatmullRom
    not applied     : photometric gain, clip census, outlier rejection, halo
                      correction, through-focus statistics

The last of those is the binary stating its own ABSENT stages, which is exactly
the fact this project spent an evening inferring wrongly from an argv.  A
whitelist drops whatever nobody thought to enumerate, so the fix was to carry
the whole self-report verbatim.  Renders after that change carry it; the 26
masters already delivered do not, and their per-subject logs are still on disk,
so they can be back-filled rather than re-rendered.

PAIRING GUARD
-------------
A sidecar is matched to a log by filename convention.  That convention could be
wrong, and silently attaching subject A's resolved state to subject B's master
would be worse than attaching none.  So the log must independently name the
artifact in its own `wrote :` line, and a sidecar whose log fails that check is
refused, not guessed at.

The summary partitions every sidecar into counted outcomes that sum to the
total, so a skipped file cannot be read as a completed one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

INDEX_HDR = "BINARY-REPORTED RESOLVED STATE (the binary's own banner, not inferred)"
STALE_LINE = "  These are the lines where the binary states what it actually did:"
STALE_ARGV = "FULL ARGV (verbatim, as executed):"
FIXED_ARGV = "ARGV (verbatim, as executed -- NOT the whole switch state; see below):"
VERBATIM_HDR = "BINARY SELF-REPORT, VERBATIM"
REPRO_HDR = "REPRODUCE THIS EXACT FILE:"


def fix_argv_header(sidecar: Path) -> str:
    """Retract the word FULL from a header that was never the full state.

    The delivered sidecars call the argv line `FULL ARGV (verbatim, as
    executed)`.  It is verbatim and it is argv, but it is not full: the
    environment switches, the gear guards and the compiled defaults cannot
    appear in an argv at all.  A header claiming completeness over an
    incomplete record is what invites the reader to stop looking.
    """
    text, nl = read_text(sidecar)
    if STALE_ARGV not in text:
        return "already-correct"
    sidecar.write_bytes(text.replace(STALE_ARGV, FIXED_ARGV).encode("utf-8"))
    return "fixed"


def read_text(p: Path) -> tuple[str, str]:
    """Return (text, line terminator), preserving the file's own terminator."""
    raw = p.read_bytes().decode("utf-8")
    return raw, "\r\n" if "\r\n" in raw else "\n"


def supplement(sidecar: Path) -> str:
    text, nl = read_text(sidecar)
    if VERBATIM_HDR in text:
        return "already-present"

    artifact = sidecar.name[: -len(".provenance.txt")]
    log = sidecar.with_name(artifact.rsplit(".", 1)[0] + ".log")
    if not log.exists():
        return "no-log"

    log_text, _ = read_text(log)
    wrote = [ln for ln in log_text.splitlines() if ln.lstrip().startswith("wrote")]
    if not wrote or artifact not in wrote[0]:
        return "pairing-mismatch"

    lines = text.splitlines()
    if REPRO_HDR not in lines:
        return "no-repro-anchor"

    log_lines = log_text.splitlines()
    keys = sum(
        1
        for ln in log_lines
        if ":" in ln and ln[:1].isalpha() and ln.split(":", 1)[1].strip()
    )
    block = [
        "",
        f"{VERBATIM_HDR} ({len(log_lines)} lines, nothing filtered)",
        "  Back-filled from this render's own log after the capture above was",
        f"  measured to be a {keys}-key whitelist that dropped the binary's",
        "  alignment, resampler and 'not applied' lines.  Nothing is filtered here.",
        *["  | " + ln for ln in log_lines],
    ]

    # The old index claimed to be the complete set of state lines.  It was not,
    # and leaving that claim in place beside a verbatim block that contradicts
    # it would be worse than the original gap.
    out: list[str] = []
    for ln in lines:
        if ln == STALE_LINE:
            out.append("  This is an INDEX, not a filter: the binary's complete")
            out.append("  self-report follows verbatim below.  A key missing from")
            out.append("  this index is still present in the record.")
            continue
        if ln == REPRO_HDR:
            out.extend(block)
            out.append("")
        out.append(ln)

    sidecar.write_bytes((nl.join(out) + nl).encode("utf-8"))
    return "appended"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    args = ap.parse_args()

    sidecars = sorted(args.root.glob("*.provenance.txt"))
    if not sidecars:
        print(f"NO SIDECARS under {args.root} -- nothing examined, which is not a pass")
        return 1

    tally: dict[str, list[str]] = {}
    hdr: dict[str, int] = {}
    for s in sidecars:
        tally.setdefault(supplement(s), []).append(s.name)
        k = fix_argv_header(s)
        hdr[k] = hdr.get(k, 0) + 1

    print(f"sidecars found     : {len(sidecars)}")
    total = 0
    for outcome in sorted(tally):
        names = tally[outcome]
        total += len(names)
        print(f"  {outcome:<18}: {len(names)}")
        if outcome in ("no-log", "pairing-mismatch", "no-repro-anchor"):
            for n in names[:5]:
                print(f"      {n}")
    print(f"  {'TOTAL':<18}: {total}  (must equal {len(sidecars)})")

    print("argv header ('FULL ARGV' claims a completeness argv cannot have):")
    ht = 0
    for k in sorted(hdr):
        ht += hdr[k]
        print(f"  {k:<18}: {hdr[k]}")
    print(f"  {'TOTAL':<18}: {ht}  (must equal {len(sidecars)})")

    bad = sum(len(v) for k, v in tally.items() if k not in ("appended", "already-present"))
    if total != len(sidecars) or ht != len(sidecars) or bad:
        print("REFUSED -- some sidecars were not supplemented")
        return 1
    print("SELF-REPORT BACK-FILL COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
