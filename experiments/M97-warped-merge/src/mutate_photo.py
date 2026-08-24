"""M97q F2b RED CONTROL: break the noise propagation, leave the gain applied.

Turns the wiring into precisely the bug M99 warns is silent -- data scaled by
c, noise model held -- so the focus ratio contrast/sigma is no longer
invariant. If F2's 0 px is a real null rather than a dead probe, THIS must
re-elect a large fraction of the plane.

Anchored on a unique full line, with an occurrence-count assertion and a hard
error if the target is not found: a mutation that silently fails to land
manufactures a green. Restores from a $TEMP copy, never `git checkout --`.
"""

import pathlib
import shutil
import sys

SRC = pathlib.Path(
    r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\src\merge_cmd.rs"
)
BACKUP = pathlib.Path(r"C:\dev\strehl-out\M97\merge_cmd.rs.M97q-backup")

ANCHOR = "                    noise = &scaled_noise;\n"
PLANT = "                    noise = self.noise;\n                    let _ = &scaled_noise;\n"


def apply():
    text = SRC.read_text(encoding="utf-8")
    n = text.count(ANCHOR)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: expected exactly 1 occurrence of the "
            f"propagation line, found {n}. Refusing to build a control whose "
            f"mutation did not land."
        )
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, BACKUP)
    SRC.write_text(text.replace(ANCHOR, PLANT), encoding="utf-8")
    after = SRC.read_text(encoding="utf-8")
    if ANCHOR in after or PLANT not in after:
        raise SystemExit("MUTATION DID NOT LAND: refusing to proceed.")
    print("PLANTED: noise propagation disabled, gain still applied")


def restore():
    if not BACKUP.exists():
        raise SystemExit("NO BACKUP: refusing to guess at the original text.")
    shutil.copy2(BACKUP, SRC)
    text = SRC.read_text(encoding="utf-8")
    if ANCHOR not in text or PLANT in text:
        raise SystemExit("RESTORE FAILED: the tree is shared -- fix this by hand NOW.")
    print("RESTORED: propagation line is back")


if __name__ == "__main__":
    {"apply": apply, "restore": restore}[sys.argv[1]]()
