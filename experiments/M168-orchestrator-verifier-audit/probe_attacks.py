#!/usr/bin/env python3
"""Adversarial probes for generativity classification and Amendment 6 SHA checks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
AUDIT_COMMIT = "f267bbccfd450982720f747c64e383376df2c4f9"


def run(script: Path, cwd: Path, env: dict[str, str] | None = None, args: tuple[str, ...] = ()) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def picked(output: str) -> str:
    wanted = []
    for line in output.splitlines():
        if "default_rng" in line or "exit under" in line or line.startswith("VERDICT:") or "MISMATCH" in line:
            wanted.append(line.strip())
    return " | ".join(wanted)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="M168-orch-probes-") as td:
        root = Path(td) / "repo"
        archive = Path(td) / "snapshot.zip"
        proc = subprocess.run(
            [
                "git", "-C", str(REPO), "archive", "--format=zip",
                f"--output={archive}", AUDIT_COMMIT,
                "experiments/ORCH-verify", "experiments/M164-m2-repair",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stdout)
        shutil.unpack_archive(archive, root)

        probe = root / "experiments" / "ORCH-verify" / "probe_generativity.py"
        target = root / "experiments" / "M164-m2-repair" / "verify.py"
        stored = target.parent / "stored.json"
        original_target = target.read_bytes()

        rc, output = run(probe, root, args=(str(target),))
        print(f"CURRENT_TARGET probe_exit={rc} | {picked(output)}")
        if rc != 0 or "VERDICT: GENERATIVE" not in output:
            raise AssertionError(output)

        stored.write_text("{\"accepted\": true}\n", encoding="utf-8")
        cosmetic = """import json\nimport sys\nimport numpy as np\ntry:\n    np.random.default_rng(7)\nexcept RuntimeError:\n    raise SystemExit(99)\nwith open(\"experiments/M164-m2-repair/stored.json\", encoding=\"utf-8\") as f:\n    json.load(f)\nprint(\"PASS: stored result accepted\")\n"""
        target.write_text(cosmetic, encoding="utf-8")
        plain_rc, plain_output = run(target, root)
        probe_rc, probe_output = run(probe, root, args=(str(target),))
        print(f"COSMETIC_TARGET direct_exit={plain_rc} direct_output={plain_output.strip()}")
        print(f"COSMETIC_TARGET probe_exit={probe_rc} | {picked(probe_output)}")
        if plain_rc != 0 or probe_rc != 0 or "VERDICT: GENERATIVE" not in probe_output:
            raise AssertionError(probe_output)

        no_rng = """import json\nwith open(\"experiments/M164-m2-repair/stored.json\", encoding=\"utf-8\") as f:\n    json.load(f)\nprint(\"PASS: stored result accepted\")\n"""
        target.write_text(no_rng, encoding="utf-8")
        probe_rc, probe_output = run(probe, root, args=(str(target),))
        print(f"NO_RNG_TARGET probe_exit={probe_rc} | {picked(probe_output)}")
        if probe_rc != 0 or "VERDICT: NOT GENERATIVE" not in probe_output:
            raise AssertionError(probe_output)
        target.write_bytes(original_target)

        env = os.environ.copy()
        git_dir = subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "--absolute-git-dir"], text=True
        ).strip()
        env["GIT_DIR"] = git_dir
        env["GIT_WORK_TREE"] = str(root)
        check1 = root / "experiments" / "ORCH-verify" / "check_amd6_sha.py"
        check2 = root / "experiments" / "ORCH-verify" / "check_amd6_sha2.py"
        rc1, out1 = run(check1, root, env)
        rc2, out2 = run(check2, root, env)
        print(f"SHA_PROBE_1 exit={rc1} | {picked(out1)}")
        print(f"SHA_PROBE_2 exit={rc2} | {picked(out2)}")
        if rc1 != 0 or "MISMATCH" not in out1:
            raise AssertionError(out1)
        if rc2 != 0 or "figure is CORRECT" not in out2:
            raise AssertionError(out2)

        wrong = Path(td) / "wrong_sha_probe.py"
        source = check2.read_text(encoding="utf-8")
        expected = "418D2D852DC15B072CB65DD6BAAECAA9B4CBF82843BA825F00B0440ACC733C43"
        if source.count(expected) != 1:
            raise AssertionError("claimed SHA anchor is not unique")
        wrong.write_text(source.replace(expected, "0" * 64), encoding="utf-8")
        wrong_rc, wrong_output = run(wrong, root, env)
        print(f"WRONG_SHA_CLAIM probe_exit={wrong_rc} | {picked(wrong_output)}")
        if wrong_rc != 0 or "Real defect" not in wrong_output:
            raise AssertionError(wrong_output)

    print("PROBE_ATTACKS: ALL REPRODUCED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
