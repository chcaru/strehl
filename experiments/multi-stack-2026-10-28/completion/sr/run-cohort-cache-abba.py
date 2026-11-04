"""Root-scheduled serial ABBA of two original-CFA resident cache budgets."""
from pathlib import Path
import json
import subprocess
import sys

root = Path("outputs/multi-stack/completion")
for arm, slots in enumerate((69, 127, 127, 69), 1):
    command = [sys.executable, "experiments/multi-stack-2026-10-28/run-command.py",
               "--receipt", str(root / f"sr-cohort-cache-run-{arm:02}"), "--cwd", ".", "--",
               str(root / "sr-cohort-cache-build-03/cohort-cache-replay.exe"),
               "outputs/multi-stack/manifests/slide-hdr-pair.json",
               str(root / "sr-chart-native-14c/source-identities.json"),
               str(root / "hdr-source-cache-current"), str(root / "sr-cohort-trace-01.json"),
               str(root / f"sr-cohort-cache-arm-{arm:02}.json"), str(slots)]
    subprocess.run(command, check=True)
reports = [json.loads((root / f"sr-cohort-cache-arm-{arm:02}.json").read_text()) for arm in range(1, 5)]
assert len({r["observed_originals_sha256"] for r in reports}) == 1
assert len({r["trace_sha256"] for r in reports}) == 1
assert all(r["cache"]["decodes"] == 0 for r in reports)
summary = {"schema": "strehl.reconstruction-cohort-cache-abba.v1", "arms": reports,
           "all_original_observations_equal": True,
           "scope": "Concurrent full reconstruction and UI/research activity; source-cache preparation only, not isolated full-render speed."}
with (root / "sr-cohort-cache-abba-01.json").open("x", encoding="utf-8") as out:
    json.dump(summary, out, indent=2)
    out.write("\n")
print(json.dumps(summary, indent=2))
