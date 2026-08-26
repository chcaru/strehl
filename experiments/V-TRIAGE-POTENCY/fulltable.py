#!/usr/bin/env python3
"""End-to-end: run triage.main() over the whole 26-subject corpus with ONE
subject's compare evidence replaced by a planted-defect run, and show that the
shipped table prints a non-zero MERGE-LIMITED row.

Everything is copied into a scratch tree; BUILD-TRIAGE's own JSON is read-only.
"""
from __future__ import annotations

import os
import shutil
import sys
import time

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402

SRC = r"C:\dev\strehl-out\BUILD-TRIAGE"
DST = r"C:\dev\strehl-out\V-TRIAGE-POTENCY\fulltable"


def main() -> int:
    swap_sub, swap_root = sys.argv[1], sys.argv[2]
    for kind in ("focus", "motion", "compare"):
        os.makedirs(os.path.join(DST, kind), exist_ok=True)
        for s in tri.SUBJECTS:
            src = os.path.join(SRC, kind, s + ".json")
            if os.path.exists(src):
                dst = os.path.join(DST, kind, s + ".json")
                shutil.copyfile(src, dst)
                os.utime(dst, None)
    planted = os.path.join(swap_root, "compare", swap_sub + ".json")
    if not os.path.exists(planted):
        raise SystemExit(f"ANCHOR MISSING: {planted}")
    target = os.path.join(DST, "compare", swap_sub + ".json")
    shutil.copyfile(planted, target)
    now = time.time()
    os.utime(target, (now, now))
    print(f"swapped in {planted}\n        -> {target}")
    print(f"        mtime {time.ctime(os.path.getmtime(target))} "
          f"size {os.path.getsize(target)}")
    a = open(planted, encoding="utf-8").read()
    b = open(target, encoding="utf-8").read()
    assert a == b, "SWAP DID NOT LAND: copied file differs from the planted one"
    print("        swap verified byte-identical")

    tri.OUT = DST
    import triage  # noqa: E402
    return triage.main()


if __name__ == "__main__":
    raise SystemExit(main())
