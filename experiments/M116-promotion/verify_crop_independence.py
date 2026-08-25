"""Prove the crop-window bug could not have touched the metrics.

The crop windows are used only to decide which pixels a human looks at. The
masks that N, D and Q are computed over come from quantiles of the whole
structure field and never reference a window. That is an argument; this is the
measurement. Compares every arm's N/D/Q from the scores.json written BEFORE the
crop fix against the one written after.
"""
import json
import sys
from pathlib import Path

before = json.loads(Path(sys.argv[1]).read_text())
after = json.loads(Path(sys.argv[2]).read_text())

checked = differ = 0
for subj, groups in after.items():
    for group, g in groups.items():
        if not g or subj not in before or group not in before[subj]:
            continue
        b = before[subj][group]
        if not b:
            continue
        for arm, s in g.get("arms", {}).items():
            if arm not in b.get("arms", {}):
                continue
            for k in ("N", "D", "Q", "sha256"):
                checked += 1
                if b["arms"][arm][k] != s[k]:
                    differ += 1
                    print(f"  DIFFERS {subj}/{group}/{arm}/{k}: "
                          f"{b['arms'][arm][k]} -> {s[k]}")

print(f"compared {checked} metric values across arms; {differ} differ")
print("PASS - the crop-window fix moved no metric" if differ == 0
      else "FAIL - metrics moved, they were NOT independent of the crop window")
sys.exit(1 if differ else 0)
