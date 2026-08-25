"""M87 / probe -- negative control for the AST-based smuggling check.

fix_s36_classify.py replaced verify_s32's regex smuggling check with a
structural AST match. That made verify_s32 go from RED to GREEN, and a check
that stops firing is indistinguishable from a check that was deleted. So the
strengthened form has to be shown to still catch the thing it exists for.

Four arms, and all four must land or the control proves nothing:

  A  baseline                        expect rc = 0
  B  plant a real rawpy.imread call  expect rc = 1, naming the file
  C  plant a real np.load(CACHE...)  expect rc = 1, naming the file
  D  plant only a QUOTATION of the   expect rc = 0 -- this is the false
     reader name in a string             positive the change exists to fix

Restore is by exact string equality against a copy taken before the plant.
`git checkout -- <path>` is never used: it reverts to HEAD and would destroy
uncommitted work belonging to other agents in this shared tree.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parents[2]
TARGET = SRC / "fix_s36_wire.py"          # harness-prefixed, measures nothing
V32 = SRC / "verify_s32.py"

PLANTS = {
    "B": ('rawpy call', '\n\ndef _planted():\n    import rawpy\n'
                        '    return rawpy.imread("x.ARW")\n', 1),
    "C": ('np.load(CACHE)', '\n\ndef _planted():\n    import numpy as np\n'
                            '    CACHE = "."\n    return np.load(CACHE / "a.npy")\n', 1),
    "D": ('quotation only', '\n\n_PLANTED_PROSE = "the reader of record is '
                            'rawpy.imread into raw_image_visible"\n', 0),
}


def run():
    p = subprocess.run([sys.executable, str(V32)], cwd=str(ROOT),
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    original = TARGET.read_bytes()
    keep = pathlib.Path(tempfile.gettempdir()) / (TARGET.name + ".m87s36bak")
    keep.write_bytes(original)
    fails = []

    rc, _ = run()
    print(f"  A  baseline                       rc={rc}  "
          f"{'ok' if rc == 0 else 'BASELINE NOT GREEN -- control void'}")
    if rc != 0:
        return 1

    for tag, (what, code, want) in PLANTS.items():
        TARGET.write_bytes(original + code.encode("utf-8"))
        rc, out = run()
        named = TARGET.name in out
        ok = (rc == want) and (named if want else True)
        print(f"  {tag}  plant {what:16s} rc={rc} want={want}  "
              f"named={named}  {'ok' if ok else 'MISSED'}")
        if not ok:
            fails.append(tag)
            if want:
                print("     -> the check does NOT catch a real reader call; "
                      "the AST change broke it")
            else:
                print("     -> a bare quotation still trips it; the false "
                      "positive was not actually fixed")
        TARGET.write_bytes(original)
        assert TARGET.read_bytes() == original, "restore failed for %s" % TARGET

    assert TARGET.read_bytes() == keep.read_bytes(), "final restore mismatch"
    rc, _ = run()
    print(f"  E  restored, no plant             rc={rc}  "
          f"{'ok' if rc == 0 else 'TREE LEFT DIRTY'}")
    if rc != 0:
        fails.append("E")
    keep.unlink(missing_ok=True)

    print(f"\nprobe_s32ast: {len(PLANTS) + 2} arms, {len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
