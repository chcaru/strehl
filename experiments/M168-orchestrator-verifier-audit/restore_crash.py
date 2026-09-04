#!/usr/bin/env python3
"""Demonstrate normal restore and interrupted-run recovery failure in commission_2957.

The crash is injected only into a temporary copy immediately after the first STATUS
mutation. No repository file is written.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
FROZEN_COMMIT = "f267bbccfd450982720f747c64e383376df2c4f9"
AUDIT_COMMIT = sys.argv[1] if len(sys.argv) > 1 else FROZEN_COMMIT
BACKUP_NAME = "STATUS_2957_commission_backup.md"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def invoke(script: Path, root: Path, temp: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["TEMP"] = str(temp)
    proc = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="M168-orch-restore-") as td:
        root = Path(td) / "repo"
        archive = Path(td) / "snapshot.zip"
        archived = subprocess.run(
            [
                "git", "-C", str(REPO), "archive", "--format=zip",
                f"--output={archive}", AUDIT_COMMIT, "docs",
                "experiments/ORCH-verify", "experiments/M136-m8o-bar",
                "experiments/M163-m10-uncertainty",
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        if archived.returncode != 0:
            raise AssertionError(archived.stdout)
        shutil.unpack_archive(archive, root)
        m134_source = REPO / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
        if m134_source.exists():
            m134_bytes = m134_source.read_bytes()
            if hashlib.sha256(m134_bytes).hexdigest().upper() != "8EA64C98795E51BC007E04775866C2145D1E2D6CFBA9F4F13B8413A3721FD1EF":
                raise AssertionError("untracked M134 dependency changed after audit")
        else:
            m134_bytes = b"M168 clean-clone fixture: 13.314850036584688\n"
        m134_dest = root / "experiments" / "M134-kernel-frontier" / "M137-clamped-detail.md"
        m134_dest.parent.mkdir(parents=True)
        m134_dest.write_bytes(m134_bytes)

        status = root / "docs" / "STATUS.md"
        commission = root / "experiments" / "ORCH-verify" / "commission_2957.py"
        original_status = status.read_bytes()
        original_script = commission.read_text(encoding="utf-8")

        normal_temp = Path(td) / "normal-temp"
        normal_temp.mkdir()
        rc, output = invoke(commission, root, normal_temp)
        normal_backup = (normal_temp / BACKUP_NAME).read_bytes()
        normal_ok = status.read_bytes() == original_status == normal_backup
        print(f"NORMAL exit={rc}")
        for line in output.splitlines():
            if line.startswith("restore") or line.startswith("final run") or line.startswith("controls") or line.startswith("VERDICT:"):
                print(line)
        print(f"NORMAL_ORIGINAL_SHA={sha(original_status)}")
        print(f"NORMAL_RESTORE_BYTE_IDENTICAL={normal_ok}")
        if rc != 0 or "VERDICT: COMMISSIONED" not in output or not normal_ok:
            raise AssertionError(output)

        status.write_bytes(original_status)
        crash_temp = Path(td) / "crash-temp"
        crash_temp.mkdir()
        needle = "            STATUS.write_text(text.replace(anchor, replacement, 1), encoding=\"utf-8\")"
        if original_script.count(needle) != 1:
            raise AssertionError("mutation-write anchor is not unique")
        injected = original_script.replace(needle, needle + "\n            os._exit(77)")
        commission.write_text(injected, encoding="utf-8")

        crash_rc, _ = invoke(commission, root, crash_temp)
        mutated_status = status.read_bytes()
        backup_after_crash = (crash_temp / BACKUP_NAME).read_bytes()
        recoverable = mutated_status != original_status and backup_after_crash == original_status
        print(f"INJECTED_CRASH_EXIT={crash_rc}")
        print(f"STATUS_MUTATED_AFTER_CRASH={mutated_status != original_status}")
        print(f"ORIGINAL_BACKUP_RECOVERABLE_AFTER_CRASH={recoverable}")
        if crash_rc != 77 or not recoverable:
            raise AssertionError("injected crash did not produce the expected recoverable state")

        commission.write_text(original_script, encoding="utf-8")
        retry_rc, retry_output = invoke(commission, root, crash_temp)
        backup_after_retry = (crash_temp / BACKUP_NAME).read_bytes()
        original_backup_destroyed = backup_after_retry == mutated_status and backup_after_retry != original_status
        status_still_mutated = status.read_bytes() == mutated_status and mutated_status != original_status
        print(f"RETRY_EXIT={retry_rc}")
        for line in retry_output.splitlines():
            if line.startswith("precondition") or line.startswith("ERROR:"):
                print(line)
        print(f"ORIGINAL_BACKUP_DESTROYED={original_backup_destroyed}")
        print(f"STATUS_STILL_MUTATED={status_still_mutated}")
        print(f"MUTATED_SHA={sha(mutated_status)}")
        if retry_rc == 0 or not original_backup_destroyed or not status_still_mutated:
            raise AssertionError(retry_output)

    print("RESTORE_ATTACK: REPRODUCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
