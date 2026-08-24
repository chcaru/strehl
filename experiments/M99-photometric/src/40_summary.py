"""Compact summary of the M99 Phase A/B result files, for the report."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def main() -> None:
    a = json.load(open(os.path.join(DATA, "phaseA.json"), encoding="utf-8"))
    print("== Phase A ==")
    for stack, d in a.items():
        keys = [k for k in d if not isinstance(d[k], list)]
        print(stack, {k: d[k] for k in keys})
    b = json.load(open(os.path.join(DATA, "phaseB-flux.json"), encoding="utf-8"))
    print("\n== Phase B (flux) ==")
    for stack, d in b.items():
        if not isinstance(d, dict):
            print(stack, d)
            continue
        keys = [k for k in d if not isinstance(d[k], (list, dict))]
        print(stack, {k: d[k] for k in keys})
        for k in d:
            if isinstance(d[k], dict):
                inner = {j: d[k][j] for j in d[k] if not isinstance(d[k][j], list)}
                print("   ", k, inner)


if __name__ == "__main__":
    main()
