"""How many of my read-only verifiers are broken in the mode their callers use?

k18_gate702.py established the failure on verify_s20.py. This asks how wide it
is across the milestone's gates, and it has to run BEFORE the repair, because
patching destroys the evidence.

Only the read-only verify_*.py gates are run. The negctl_*.py controls mutate
the report on disk and are deliberately NOT executed in a mode designed to make
them crash -- inducing a fault in a script whose job is to restore a file is a
bad trade for a number I can get another way.

Each gate is run twice, identically, differing only in PYTHONIOENCODING, with
stdout on a PIPE exactly as an agent tool call or a CI log has it. A gate is
EXPOSED if the two runs disagree on anything a caller reads: the exit code, the
number of result lines, or whether a verdict was printed at all.

Absolute pass/fail is not the subject here and is not judged. A gate that is
RED in both modes is consistent and therefore not exposed; a gate that is GREEN
in one mode and silent in the other is the defect.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[3]
GATES = sorted(
    list((ROOT / "experiments" / "M95-kernel" / "src").glob("verify_*.py"))
    + list((ROOT / "experiments" / "M95-coverage" / "src").glob("verify_*.py"))
)


def run(script, encoding):
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    if encoding is None:
        env.pop("PYTHONIOENCODING", None)
    else:
        env["PYTHONIOENCODING"] = encoding
    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, cwd=str(ROOT), env=env
    )
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    return {
        "rc": r.returncode,
        "lines": len([ln for ln in out.splitlines() if ln.strip()]),
        "chars": len(out),
        "verdict": "GREEN" if "GREEN" in out else ("RED" if "RED" in out else "NONE"),
        "uerr": "UnicodeEncodeError" in err,
    }


print("=" * 92)
print("k18b -- fleet check: read-only gates run in the caller's mode (stdout piped)")
print("=" * 92)
print(f"{'gate':<34} {'rc(utf8)':>8} {'rc(unset)':>9} {'lines':>12} {'verdict':>16}  exposed")
print("-" * 92)

rows = []
n_exposed = 0
for g in GATES:
    u = run(g, "utf-8")
    d = run(g, None)  # unset: the true default, what a caller gets by accident
    exposed = (
        u["rc"] != d["rc"]
        or u["lines"] != d["lines"]
        or u["verdict"] != d["verdict"]
        or d["uerr"]
    )
    n_exposed += bool(exposed)
    name = f"{g.parents[1].name}/{g.name}"
    print(
        f"{name:<34} {u['rc']:>8} {d['rc']:>9} "
        f"{str(u['lines']) + '->' + str(d['lines']):>12} "
        f"{u['verdict'] + '->' + d['verdict']:>16}  {'YES' if exposed else 'no'}"
    )
    rows.append({"gate": name, "utf8": u, "unset": d, "exposed": bool(exposed)})

print("-" * 92)
print(f"{n_exposed} of {len(GATES)} read-only gates are EXPOSED")
lost = sum(r["utf8"]["chars"] - r["unset"]["chars"] for r in rows if r["exposed"])
print(f"characters of verification output lost across the exposed gates: {lost}")
print("note: negctl_*.py were not run here, by design -- see the module docstring")

out = ROOT / "experiments" / "M95-kernel" / "out"
out.mkdir(exist_ok=True)
(out / "k18b_gates.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
print("wrote out/k18b_gates.json")
print("=" * 92)
