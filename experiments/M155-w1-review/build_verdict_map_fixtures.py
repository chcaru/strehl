#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_case(source, destination):
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    a = p.parse_args()
    source = a.source.resolve()
    parent = a.destination.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    root = copy_case(source, parent / "invalid-as-go")
    contract = load(root / "contract.json")
    contract["verdicts"]["invalid_instrument"] = "PHASE1_GO"
    write(root / "contract-invalid-as-go.json", contract)
    root = copy_case(source, parent / "awaiting-as-go")
    contract = load(root / "contract.json")
    contract["verdicts"]["awaiting_holdout"] = "PHASE1_GO"
    write(root / "contract-awaiting-as-go.json", contract)
    result = load(root / "result.json")
    result["contract_sha256"] = sha(root / "contract-awaiting-as-go.json")
    result["holdout"] = None
    write(root / "result-no-holdout.json", result)
    print(json.dumps({"cases": ["invalid-as-go", "awaiting-as-go"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
