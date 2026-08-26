"""Retro-fit the resolved switch state onto sidecars written before it existed.

SHIP-V2-ICC's 26 masters were rendered before finalpass.ps1 recorded switch
state, so their sidecars list argv alone. That is the exact silence that let a
reviewer conclude, from the evidence the sidecar offered, that the owner's
masters had been rendered with lateral-CA correction switched off.

A re-render would cost 33 minutes and change nothing: the information is already
on disk, because the binary printed what it resolved to and the harness captured
its stdout per subject. This recovers it from those logs and appends a dated
SUPPLEMENT block to each sidecar. Additive only -- nothing already written is
altered, so a hash taken of the original body still describes the same render.

The claim this defends is narrow and stated as such: it recovers what the BINARY
REPORTED. The environment of that run is not recoverable after the fact, and
this script does not pretend otherwise -- it says so in the block it writes.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys

ARM = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2-ICC")
MARK = "SUPPLEMENT -- RESOLVED SWITCH STATE, RECOVERED FROM THE RUN LOG"
KEYS = re.compile(r"^\s*(merge backend|camera|lateral CA|iso|bands|selection)\s*:")


def main() -> int:
    if not ARM.is_dir():
        print(f"missing arm: {ARM}")
        return 2

    masters = sorted(ARM.glob("*.tiff"))
    if not masters:
        print(f"no masters under {ARM}")
        return 2

    added = already = no_log = no_sidecar = no_ca = 0
    stamp = dt.date.today().isoformat()

    for m in masters:
        sc = m.with_suffix(".tiff.provenance.txt")
        if not sc.exists():
            no_sidecar += 1
            continue

        body = sc.read_text(encoding="utf-8", errors="replace")
        if MARK in body:
            already += 1
            continue

        stem = m.stem
        lines: list[str] = []
        for cand in (ARM / f"{stem}.log.out", ARM / f"{stem}.log"):
            if cand.exists():
                lines += cand.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            no_log += 1
            continue

        state = [ln.strip() for ln in lines if KEYS.match(ln)]
        if not any(ln.startswith("lateral CA") for ln in state):
            no_ca += 1
            continue

        block = [
            "",
            MARK,
            f"  Appended {stamp}. The block above was written before this harness",
            "  recorded switch state; argv alone cannot show an environment switch,",
            "  and a gear-guarded one acts while reading '(unset)'. These lines are",
            "  what THIS subject's binary printed about what it actually did:",
            "",
            *(f"  {ln}" for ln in state),
            "",
            "  Scope, stated honestly: this recovers the BINARY'S OWN REPORT from the",
            "  captured stdout of this run. The environment that run saw is not",
            "  recoverable after the fact and is not claimed here. Renders made after",
            "  this date carry the full 33-switch resolved state inline instead.",
        ]
        sc.write_text(body.rstrip("\n") + "\n" + "\n".join(block) + "\n", encoding="utf-8")
        added += 1

    total = len(masters)
    print(f"masters: {total}")
    print(f"  supplement added        {added:3d}")
    print(f"  already had one         {already:3d}")
    print(f"  no run log found        {no_log:3d}")
    print(f"  no sidecar found        {no_sidecar:3d}")
    print(f"  log lacked a CA line    {no_ca:3d}")
    s = added + already + no_log + no_sidecar + no_ca
    print(f"  (sums to {s} of {total})")
    assert s == total, "outcomes do not partition the masters"
    return 0 if (no_log == no_sidecar == no_ca == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
