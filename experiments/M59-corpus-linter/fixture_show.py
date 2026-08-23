"""Print the unfiltered linter output for each fixture that is expected to fire.

Discipline 351: a red exit code is not evidence of the red you wanted. This
prints what the reader would actually see, so the report can quote it.

Imports fixture_probe, which is safe only because that module has an
`if __name__ == "__main__"` guard (AGENTS: an unguarded script was once silently
re-executed by an import).

Run: python experiments/M59-corpus-linter/fixture_show.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_probe as fp


def main():
    for name, expect, only, needle, text in fp.FIXTURES:
        if expect not in ("fire", "advisory"):
            continue
        code, out = fp.run(text, only, advisory=(expect == "advisory"))
        print("=" * 78)
        print("%s   [expect %s]" % (name, expect))
        print("=" * 78)
        for line in out.split("\n"):
            if line.startswith("corpus_lint: %d markdown" % 1):
                continue
            print(line.rstrip())
        print("exit code: %d" % code)
        print("")
    fp.rmtree(fp.PROBE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
