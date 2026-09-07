"""Report rustfmt debt without modifying unrelated historical source.

Checks every owned new test file in full and reports whether formatting deltas
touch any changed production line. Full-file rustfmt remains a reported failure
when historical formatting differs; this does not claim the whole file is clean.
"""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCT = ROOT / "crates/strehl-cli/src/merge_cmd.rs"
TESTS = [ROOT / "crates/strehl-cli/src/merge_cmd/production-truth.rs",
         HERE / "independent-controls.rs"]


def main():
    raw = PRODUCT.read_bytes()
    source = raw.decode("utf-8")
    command = ["rustfmt", "--edition", "2024", "--config", "skip_children=true"]
    formatted = subprocess.run(command, input=raw, cwd=ROOT, capture_output=True)
    if formatted.returncode:
        sys.stderr.buffer.write(formatted.stderr)
        return formatted.returncode
    a, b = source.splitlines(), formatted.stdout.decode("utf-8").splitlines()
    diff = subprocess.check_output(["git", "diff", "--unified=0", "--", str(PRODUCT)], cwd=ROOT)
    owned = set()
    for start, count in re.findall(rb"^@@.*\+(\d+)(?:,(\d+))? @@", diff, re.MULTILINE):
        start, count = int(start), int(count or b"1")
        owned.update(range(start, start + count))
    deltas = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        touched = set(range(i1 + 1, max(i1 + 2, i2 + 1)))
        deltas.append({"operation": op, "source_line": i1 + 1,
                       "source_lines": i2 - i1, "formatted_lines": j2 - j1,
                       "touches_changed_production_line": bool(touched & owned)})
    (HERE / "remaining-format.diff").write_text(
        "\n".join(difflib.unified_diff(a, b, fromfile="current", tofile="rustfmt", lineterm="")) + "\n",
        encoding="utf-8")
    tests = []
    for path in TESTS:
        cmd = command + ["--check", str(path)]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True)
        log = HERE / (path.stem + "-format.log")
        log.write_bytes(result.stdout + result.stderr)
        tests.append({"path": str(path.relative_to(ROOT)), "command": cmd,
                      "exit_code": result.returncode, "log": log.name})
    record = {
        "schema": "m194-format-scope-v1",
        "command_stdin": command,
        "production_sha256": hashlib.sha256(raw).hexdigest(),
        "full_production_file_formatted": not deltas,
        "remaining_production_deltas": deltas,
        "changed_production_lines_formatted": not any(d["touches_changed_production_line"] for d in deltas),
        "test_files": tests,
    }
    record["owned_scope_pass"] = record["changed_production_lines_formatted"] and all(t["exit_code"] == 0 for t in tests)
    (HERE / "format-verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if record["owned_scope_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
