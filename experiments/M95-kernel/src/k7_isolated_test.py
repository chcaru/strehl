"""Prove arm 9's code compiles and passes tests, without touching M100's file.

`crates/strehl-core/src/color.rs` is M100's, it is dirty in the shared tree,
and its in-flight state does not compile. That blocks `cargo test -p
strehl-core` for everyone, including me, and it is not mine to fix or revert.

So: copy the workspace sources to a scratch directory, put the **committed**
`color.rs` back in the copy only, and run the tests there. The live tree is
never written to. `color.rs` is restored from the HEAD blob read as **bytes**
via subprocess -- never `git show > file`, which re-encodes the stream on
Windows and would silently corrupt the comparison.

Run: `python experiments/M95-kernel/src/k7_isolated_test.py`
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = Path(os.environ["TEMP"]) / "m95-isolated"
CARGO = Path(os.environ["USERPROFILE"]) / ".cargo" / "bin" / "cargo.exe"
COLOR = "crates/strehl-core/src/color.rs"


def head_bytes(rel):
    p = subprocess.run(
        ["git", "show", f"HEAD:{rel}"], cwd=str(ROOT), capture_output=True, check=True
    )
    return p.stdout


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)

    for name in ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml", ".rustfmt.toml"]:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, SCRATCH / name)
    shutil.copytree(ROOT / "crates", SCRATCH / "crates")
    print(f"copied workspace sources -> {SCRATCH}")

    blob = head_bytes(COLOR)
    live = (ROOT / COLOR).read_bytes()
    tgt = SCRATCH / COLOR
    tgt.write_bytes(blob)
    os.utime(tgt, (time.time(), time.time()))
    print(f"restored {COLOR} in the copy from HEAD: {len(live)} dirty bytes -> {len(blob)} committed bytes")
    print(f"live tree untouched: {(ROOT / COLOR).read_bytes() == live}")

    for f in ["align.rs", "warpmap.rs"]:
        a = (ROOT / "crates" / "strehl-core" / "src" / f).read_bytes()
        b = (SCRATCH / "crates" / "strehl-core" / "src" / f).read_bytes()
        print(f"  {f:<14} copied verbatim from the working tree: {a == b}")

    env = dict(os.environ, CARGO_TARGET_DIR=str(SCRATCH / "target"))
    print("\nrunning: cargo test --release -p strehl-core\n")
    p = subprocess.run(
        [str(CARGO), "test", "--release", "-p", "strehl-core"],
        cwd=str(SCRATCH),
        capture_output=True,
        text=True,
        env=env,
    )
    tail = [ln for ln in (p.stdout + p.stderr).splitlines() if "test result" in ln or ln.startswith("error")]
    print("\n".join(tail) if tail else (p.stdout + p.stderr)[-2000:])

    print("\nlanczos3 tests specifically:")
    p2 = subprocess.run(
        [str(CARGO), "test", "--release", "-p", "strehl-core", "lanczos", "--", "--nocapture"],
        cwd=str(SCRATCH),
        capture_output=True,
        text=True,
        env=env,
    )
    for ln in (p2.stdout + p2.stderr).splitlines():
        if "lanczos" in ln or "test result" in ln:
            print("  " + ln.strip())

    ok = p.returncode == 0 and p2.returncode == 0
    print(f"\n{'ISOLATED TESTS PASS' if ok else 'ISOLATED TESTS FAIL'}  (rc {p.returncode}, {p2.returncode})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
