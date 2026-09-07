"""Check new gatefloor lines without rewriting inherited formatting."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = Path("crates/strehl-cli/src/merge_cmd/gatefloor.rs")
BASE = "444eb759be0358cda25e97d4375f977a039efe6a"


def changed_rows(before, after):
    rows = set()
    for tag, _i, _j, first, last in difflib.SequenceMatcher(a=before, b=after).get_opcodes():
        if tag != "equal":
            rows.update(range(first, last))
    return rows


def main():
    current = (ROOT / SOURCE).read_text(encoding="utf-8").splitlines()
    original = subprocess.check_output(["git", "show", BASE + ":" + SOURCE.as_posix()], cwd=ROOT)
    old = original.decode("utf-8").splitlines()
    command = ["rustfmt", "--edition", "2024", "--config", "skip_children=true", "--emit", "stdout", str(SOURCE)]
    p = subprocess.run(command, cwd=ROOT, capture_output=True)
    formatted = p.stdout.decode("utf-8").splitlines()
    formatted = formatted[formatted.index(current[0]):]
    owned = changed_rows(old, current)
    unformatted = set()
    differences = []
    for tag, first, last, _i, _j in difflib.SequenceMatcher(a=current, b=formatted).get_opcodes():
        if tag != "equal":
            unformatted.update(range(first, last))
            differences.append(dict(kind=tag, current_lines=[first + 1, last], lines=current[first:last]))
    overlap = sorted(owned & unformatted)
    result = dict(schema="m194c-scoped-format-v1", command=command, exit_code=p.returncode,
                  source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                  owned_added_or_replaced_lines=sorted(n + 1 for n in owned),
                  inherited_format_differences=differences,
                  overlap_owned_lines=[n + 1 for n in overlap],
                  scope="New gatefloor lines only; full-file formatting debt is retained.")
    result["pass"] = p.returncode == 0 and not overlap
    (HERE / "format-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (HERE / "format-check.log").write_text(" ".join(command) + "\n" + json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
