#!/usr/bin/env python3
"""Reproduce semantic and linkage attacks against the ORCH verification apparatus.

All mutations occur in a TemporaryDirectory. The repository under audit is read only.
The script exits nonzero if a documented attack no longer reproduces.
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


def run(script: Path, root: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-B", str(script), str(root)],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise AssertionError(f"anchor count for {old!r}: expected {expected}, got {count}")
    return text.replace(old, new)


def summary(output: str, labels: tuple[str, ...]) -> str:
    lines = []
    for line in output.splitlines():
        if line.startswith("VERDICT:"):
            lines.append(line.strip())
        elif line.startswith(("GREEN", "RED")) and any(label in line for label in labels):
            lines.append(line.strip())
    return " | ".join(lines)


def require_green(name: str, rc: int, output: str, labels: tuple[str, ...]) -> None:
    evidence = summary(output, labels)
    print(f"FALSE_GREEN {name}: exit={rc} | {evidence}")
    if rc != 0 or "VERDICT: GREEN" not in output:
        raise AssertionError(f"attack did not remain GREEN: {name}\n{output}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="M168-orch-semantic-") as td:
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

        status_path = root / "docs" / "STATUS.md"
        m167_path = root / "docs" / "research" / "M167-detail-battery.md"
        owner_path = root / "docs" / "OWNER-ACTIONS.md"
        v2954 = root / "experiments" / "ORCH-verify" / "v2954.py"
        commission = root / "experiments" / "ORCH-verify" / "commission_2957.py"
        vowner = root / "experiments" / "ORCH-verify" / "vowner0906.py"

        original_status = status_path.read_text(encoding="utf-8")
        original_m167 = m167_path.read_text(encoding="utf-8")
        original_owner = owner_path.read_text(encoding="utf-8")
        original_commission = commission.read_text(encoding="utf-8")

        rc, out = run(v2954, root)
        print(f"BASELINE v2954: exit={rc} | {summary(out, ())}")
        if rc != 0 or "VERDICT: GREEN" not in out:
            raise AssertionError(out)

        def status_case(name: str, label: str, old: str, new: str) -> None:
            status_path.write_text(replace_exact(original_status, old, new), encoding="utf-8")
            m167_path.write_text(original_m167, encoding="utf-8")
            rc2, out2 = run(v2954, root)
            require_green(name, rc2, out2, (label,))

        status_case(
            "identity polarity reversed",
            "veto identity token",
            "does **not** fire on\nexact identity",
            "does fire on\nexact identity",
        )
        status_case(
            "recommission passed changed to failed",
            "recommission status",
            "recommissioned tonight and **passed**",
            "recommissioned tonight and **failed**",
        )
        status_case(
            "improvement plant explicitly absent",
            "improvement plant present",
            "a planted degradation **and** a planted\nimprovement",
            "no planted degradation and no planted improvement",
        )
        status_case(
            "M1 withdrawal explicitly revoked",
            "m1 withdrawn",
            "The scorecard records M1 as ",
            "The scorecard no longer records M1 as ",
        )
        status_case(
            "M2 interpretation reversed",
            "m2 battery replay",
            "— blur *improves* the score, and all three blur steps moved the favourable way",
            "— blur *worsens* the score, and all three blur steps moved the unfavourable way",
        )
        status_case(
            "96 corrupted to 97 while another 96 survives elsewhere",
            "M1 per-class frames",
            "`96` frames per additional class",
            "`97` frames per additional class",
        )

        status_path.write_text(original_status, encoding="utf-8")
        changed_source = original_m167.replace("1.0249391472947889", "1.0249391472947880")
        changed_source = changed_source.replace("0.5712148772282098", "0.5712148772282090")
        if "1.0249391472947889" in changed_source or "0.5712148772282098" in changed_source:
            raise AssertionError("source-number mutation did not remove both expected values")
        m167_path.write_text(changed_source, encoding="utf-8")
        rc, out = run(v2954, root)
        require_green("both M167 source numbers removed", rc, out, ("m137 flat beats detail", "m2 battery replay"))

        table_old = "ratio **`1.0249391472947889`** — it scores a featureless flat *above* real detail"
        table_new = "ratio **`1.0249391472947880`** — it scores a featureless flat *above* real detail"
        decoy = "\nWithdrawn false value retained only as a decoy: `1.0249391472947889`.\n"
        changed_status = replace_exact(original_status, table_old, table_new)
        marker = "#### 2.9.54.1 Four instruments repaired, and one structural discovery"
        changed_status = replace_exact(changed_status, marker, decoy + marker)
        status_path.write_text(changed_status, encoding="utf-8")
        m167_path.write_text(original_m167, encoding="utf-8")
        rc, out = run(v2954, root)
        require_green("real M137 value wrong but withdrawn decoy present", rc, out, ("m137 flat beats detail",))

        wrong_sentence_old = "**exceeded** detail gap `0.3403664343410666`; ratio **`1.0249391472947889`** — it scores a featureless flat *above* real detail"
        wrong_sentence_new = "**fell below** detail gap `0.3403664343410666`; ratio **`1.0249391472947889`** — it scores a featureless flat *below* real detail"
        status_path.write_text(replace_exact(original_status, wrong_sentence_old, wrong_sentence_new), encoding="utf-8")
        m167_path.write_text(original_m167, encoding="utf-8")
        temp_for_commission = root / "commission-temp"
        temp_for_commission.mkdir()
        env = os.environ.copy()
        env["TEMP"] = str(temp_for_commission)
        rc, out = run(commission, root, env)
        wrong_survived = wrong_sentence_new in status_path.read_text(encoding="utf-8")
        print(
            "FALSE_COMMISSION semantic inversion: "
            f"exit={rc} | {summary(out, ())} | wrong_meaning_survived_restore={wrong_survived}"
        )
        if rc != 0 or "VERDICT: COMMISSIONED" not in out or not wrong_survived:
            raise AssertionError(out)

        status_path.write_text(original_status, encoding="utf-8")
        old_mutation = (
            "    (\"m137 flat beats detail\",\n"
            "     \"ratio **`1.0249391472947889`**\",\n"
            "     \"ratio **`1.0249391472947880`**\"),"
        )
        mislabeled_mutation = (
            "    (\"m137 flat beats detail\",\n"
            "     \"blurred/unblurred = **`0.5712148772282098`**\",\n"
            "     \"blurred/unblurred = **`0.5712148772282090`**\"),"
        )
        commission.write_text(
            replace_exact(original_commission, old_mutation, mislabeled_mutation), encoding="utf-8"
        )
        mislabeled_temp = root / "mislabeled-temp"
        mislabeled_temp.mkdir()
        mislabeled_env = os.environ.copy()
        mislabeled_env["TEMP"] = str(mislabeled_temp)
        rc, out = run(commission, root, mislabeled_env)
        control_line = next(line.strip() for line in out.splitlines() if "m137 flat beats detail" in line)
        print(f"FALSE_COMMISSION wrong claim mutated: exit={rc} | {control_line} | {summary(out, ())}")
        if rc != 0 or "VERDICT: COMMISSIONED" not in out or "| RED" in control_line:
            raise AssertionError(out)
        commission.write_text(original_commission, encoding="utf-8")

        owner_path.write_text(original_owner, encoding="utf-8")
        rc, out = run(vowner, root)
        print(f"BASELINE vowner: exit={rc} | {summary(out, ())}")
        if rc != 0 or "VERDICT: GREEN" not in out:
            raise AssertionError(out)

        owner_wrong = replace_exact(
            original_owner,
            "If that pair says the optics cannot\nsupport the required sampling ratio, **the entire 1,602-frame session is\ncancelled before it is ever shot**",
            "Even if that pair says the optics cannot\nsupport the required sampling ratio, **the entire 1,602-frame session is\nmandatory and must proceed anyway**",
        )
        owner_path.write_text(owner_wrong, encoding="utf-8")
        rc, out = run(vowner, root)
        require_green("owner kill gate inverted to mandatory shoot", rc, out, ("GREEN:",))

        owner_bad_math = replace_exact(
            original_owner,
            "| Stages 1–5 — rehearsal, released one block at a time | `896` | `898` |",
            "| Stages 1–5 — rehearsal, released one block at a time | `895` | `898` |",
        )
        owner_path.write_text(owner_bad_math, encoding="utf-8")
        rc, out = run(vowner, root)
        require_green("owner table says 895 but hardcoded arithmetic says 896", rc, out, ("rehearsal frames", "arith  stages", "arith  stage 0"))

        owner_date = replace_exact(
            original_owner,
            "### Two things changed on 2026-09-06, and one of them would have wasted the whole session",
            "### Two things changed on 2026-09-04, and one of them would have wasted the whole session",
        )
        owner_path.write_text(owner_date, encoding="utf-8")
        rc, out = run(vowner, root)
        print(f"FALSE_RED corrected owner heading date: exit={rc} | {out.strip()}")
        if rc == 0 or "FATAL: owner block heading not found" not in out:
            raise AssertionError(out)

    print("AUDIT_ATTACKS: ALL REPRODUCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
