"""Run the preregistered product-path renders with complete provenance.

Capture directories are opened read-only.  Full stacks use an explicit
lane-local sidecar solved before the render.  One-frame references set
STREHL_ALIGN=0 and still name a lane-local (unused) sidecar, so no process can
read or overwrite a shared capture-side warpmap.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from veil2lib import sha256, write_json  # noqa: E402


def resolve(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def run(command: list[str], env: dict[str, str]) -> tuple[int, str, float]:
    started = time.perf_counter()
    cp = subprocess.run(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return cp.returncode, cp.stdout, time.perf_counter() - started


def clean_env() -> tuple[dict[str, str], list[str]]:
    env = dict(os.environ)
    removed = sorted(k for k in env if k.upper().startswith("STREHL_"))
    for key in removed:
        env.pop(key, None)
    env["RAYON_NUM_THREADS"] = "4"
    return env, removed


def inventory(stack: Path) -> dict:
    raws = sorted(stack.glob("*.ARW"))
    if not raws:
        raise RuntimeError(f"no ARW files in {stack}")
    return {
        "absolute_stack": str(stack.resolve()),
        "frames": len(raws),
        "first": raws[0].name,
        "last": raws[-1].name,
        "total_bytes": sum(p.stat().st_size for p in raws),
        "first_sha256": sha256(raws[0]),
        "last_sha256": sha256(raws[-1]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, default=ROOT / "render-plan.json")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    binary = Path(plan["binary"])
    got_hash = sha256(binary)
    if got_hash != plan["binary_sha256"]:
        raise SystemExit(
            f"binary hash mismatch: expected {plan['binary_sha256']}, got {got_hash}"
        )

    selected = set(args.only)
    failures = 0
    for job in plan["jobs"]:
        if selected and job["name"] not in selected:
            continue
        name = job["name"]
        stack = Path(job["stack"])
        output = resolve(ROOT, job["output"])
        warpmap = resolve(ROOT, job["warpmap"])
        record_path = ROOT / "out" / "run-records" / f"{name}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        warpmap.parent.mkdir(parents=True, exist_ok=True)
        record_path.parent.mkdir(parents=True, exist_ok=True)
        inv = inventory(stack)

        if output.exists() and not args.force:
            print(f"{name}: SKIP existing {output}")
            continue

        env, removed = clean_env()
        env["RAYON_NUM_THREADS"] = str(plan["threads"])
        env["STREHL_WARPMAP"] = str(warpmap.resolve())
        align_record = None
        only = job.get("only_frame")
        if only is None:
            if not warpmap.exists():
                align_cmd = [
                    str(binary),
                    "align",
                    str(stack),
                    "--out",
                    str(warpmap),
                    "--reference",
                    str(job["reference"]),
                    "--threads",
                    str(plan["threads"]),
                    "--resampler",
                    "catmull-rom",
                ]
                aenv = dict(env)
                aenv.pop("STREHL_WARPMAP", None)
                acode, atext, asecs = run(align_cmd, aenv)
                align_record = {
                    "command": align_cmd,
                    "environment": {
                        "STREHL_*": "all unset",
                        "RAYON_NUM_THREADS": aenv["RAYON_NUM_THREADS"],
                    },
                    "exit_code": acode,
                    "elapsed_seconds": asecs,
                    "output_text": atext,
                }
                if acode != 0:
                    write_json(
                        record_path,
                        {
                            "name": name,
                            "status": "ALIGN_FAILED",
                            "align": align_record,
                            "inventory": inv,
                        },
                    )
                    print(f"{name}: ALIGN FAILED rc={acode}")
                    failures += 1
                    continue
            env.pop("STREHL_ALIGN", None)
        else:
            env["STREHL_ONLY_FRAME"] = str(only)
            env["STREHL_ALIGN"] = "0"

        command = [
            str(binary),
            "stack",
            str(stack),
            "-o",
            str(output),
            "--merge",
            "pyramid",
            "--pyramid-bands",
            "7",
            "--pyramid-gate",
            "2.0",
            "--pyramid-exponent",
            "2.0",
            "--pyramid-sharpen",
            "1.4",
            "--pyramid-select",
            "soft",
            "--pyramid-base",
            job["base"],
            "--linear-srgb",
        ]
        started = datetime.now(timezone.utc).isoformat()
        code, text, seconds = run(command, env)
        ended = datetime.now(timezone.utc).isoformat()
        status = "OK" if code == 0 and output.exists() else "FAILED"
        record = {
            "name": name,
            "status": status,
            "source_commit": plan["source_commit"],
            "binary": str(binary),
            "binary_sha256": got_hash,
            "inventory": inv,
            "only_frame_zero_based": only,
            "command": command,
            "environment": {
                "cleared_inherited_STREHL_variables": removed,
                "STREHL_WARPMAP": env["STREHL_WARPMAP"],
                "STREHL_ONLY_FRAME": env.get("STREHL_ONLY_FRAME", "(unset)"),
                "STREHL_ALIGN": env.get("STREHL_ALIGN", "(unset/default on)"),
                "all_other_STREHL_variables": "unset",
                "RAYON_NUM_THREADS": env["RAYON_NUM_THREADS"],
            },
            "explicit_absences": [
                "--demosaic",
                "--srgb",
                "--exposure",
                "--photometric",
                "STREHL_RESTORE",
                "STREHL_FIX_CA",
                "STREHL_FIX_HALO",
            ],
            "started_utc": started,
            "ended_utc": ended,
            "elapsed_seconds": seconds,
            "exit_code": code,
            "output_text": text,
            "align": align_record,
        }
        if output.exists():
            record["artifact"] = {
                "path": str(output.resolve()),
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
            }
        if warpmap.exists() and only is None:
            record["warpmap"] = {
                "path": str(warpmap.resolve()),
                "bytes": warpmap.stat().st_size,
                "sha256": sha256(warpmap),
            }
        write_json(record_path, record)
        print(f"{name}: {status} rc={code} {seconds:.1f}s")
        if status != "OK":
            print(text[-4000:])
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

