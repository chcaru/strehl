"""Format/check owned M194d Rust changes while retaining unrelated style debt."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "04128e041dabc0bdb86c64526cd8155dd0a0fd07"
PATHS = ["crates/strehl-core/src/pyramid.rs", "crates/strehl-cli/src/merge_cmd.rs",
         "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs",
         "crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs",
         "experiments/m194d-band-admission/author-core-tests.rs"]


def owned_rows(old, current):
    return {i for tag, _a, _b, c, d in difflib.SequenceMatcher(a=old, b=current).get_opcodes()
            if tag != "equal" for i in range(c, d)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    results = []
    for relative in PATHS:
        path = ROOT / relative
        current = path.read_text(encoding="utf-8").splitlines()
        base = subprocess.run(["git", "show", BASE + ":" + relative], cwd=ROOT, capture_output=True)
        old = base.stdout.decode("utf-8").splitlines() if base.returncode == 0 else []
        command = ["rustfmt", "--edition", "2024", "--config", "skip_children=true", "--emit", "stdout", str(path)]
        p = subprocess.run(command, cwd=ROOT, capture_output=True)
        if p.returncode:
            raise RuntimeError(p.stderr.decode("utf-8", "replace"))
        formatted = p.stdout.decode("utf-8").splitlines()
        formatted = formatted[formatted.index(current[0]):]
        owned = owned_rows(old, current)
        edits = []
        inherited = []
        for tag, a, b, c, d in difflib.SequenceMatcher(a=current, b=formatted).get_opcodes():
            if tag == "equal":
                continue
            item = dict(current_lines=[a + 1, b], lines=current[a:b])
            if set(range(a, max(a + 1, b))) & owned:
                edits.append((a, b, formatted[c:d]))
            else:
                inherited.append(item)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        if args.fix and edits:
            for a, b, replacement in reversed(edits):
                current[a:b] = replacement
            path.write_text("\n".join(current) + "\n", encoding="utf-8", newline="\n")
        results.append(dict(path=relative, command=command, owned_format_changes=len(edits),
                            inherited_differences=inherited, sha256_before=before,
                            sha256_after=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(schema="m194d-scoped-format-v1", fix=args.fix, files=results,
                  passed=args.fix or all(not x["owned_format_changes"] for x in results))
    destination = HERE / ("format-fix.json" if args.fix else "format-check.json")
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["passed"], "record": str(destination)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
