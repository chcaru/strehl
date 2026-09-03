"""Run the frozen default/crop render pair and bind it to provenance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import tifffile

import cover_core as cc


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SCALE = OUT / "113-cover-scale-control.tiff"
CROP = OUT / "113-cover-crop.tiff"
PROVENANCE = OUT / "COVER-RENDER-PROVENANCE.json"
CACHE = OUT / "cache"


def render_environment() -> tuple[dict[str, str], list[str]]:
    env = dict(os.environ)
    removed = sorted(name for name in env if name.upper().startswith("STREHL_"))
    for name in removed:
        del env[name]
    env["STREHL_CACHE_DIR"] = str(CACHE.resolve())
    env["RAYON_NUM_THREADS"] = "8"
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[name] = "8"
    return env, removed


def render_one(mode: str, output: Path, env: dict[str, str]) -> dict:
    argv = cc.render_argv(mode, output)
    run = subprocess.run(
        argv,
        cwd=str(HERE.parent.parent),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log = run.stdout + ("\n" if run.stdout and run.stderr else "") + run.stderr
    if run.returncode != 0:
        print(log)
        raise RuntimeError(f"{mode} render exited {run.returncode}")
    if not output.is_file():
        raise RuntimeError(f"{mode} render produced no output")
    facts = cc.parse_render_log(log, mode)
    image = tifffile.memmap(output)
    return {
        "path": str(output.resolve()),
        "argv": argv,
        "exit_code": run.returncode,
        "sha256": cc.sha256(output),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "facts": facts,
        "log": log,
    }


def main() -> int:
    cc.verify_hashes()
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    occupied = [path for path in (SCALE, CROP, PROVENANCE) if path.exists()]
    if occupied:
        raise RuntimeError(f"refusing to overwrite existing outputs: {occupied}")
    env, removed = render_environment()
    effective_strehl = {
        name: value
        for name, value in env.items()
        if name.upper().startswith("STREHL_")
    }
    if effective_strehl != {"STREHL_CACHE_DIR": str(CACHE.resolve())}:
        raise RuntimeError(f"unexpected effective STREHL variables: {effective_strehl}")

    pre = cc.source_manifest()
    if pre["counts"] != {".arw": 63, ".xmp": 63}:
        raise RuntimeError(f"source count changed before render: {pre['counts']}")
    scale = render_one("scale", SCALE, env)
    if scale["sha256"] != cc.HASHES[cc.SCALE_MASTER]:
        raise RuntimeError(
            "scale-control byte-identity hard stop: "
            f"{scale['sha256']} != {cc.HASHES[cc.SCALE_MASTER]}"
        )
    after_scale = cc.source_manifest()
    if after_scale["digest"] != pre["digest"]:
        raise RuntimeError("source bytes changed during scale control")

    crop = render_one("crop", CROP, env)
    post = cc.source_manifest()
    if post["digest"] != pre["digest"]:
        raise RuntimeError("source bytes changed during crop render")
    cc.verify_hashes()
    payload = {
        "schema": cc.PROVENANCE_SCHEMA,
        "executable": {
            "path": str(cc.EXE),
            "sha256": cc.sha256(cc.EXE),
        },
        "source": {
            "path": str(cc.SOURCE),
            "pre": pre,
            "post": post,
        },
        "comparators": {
            name: cc.sha256(path) for name, path in cc.PMAX.items()
        },
        "environment": {
            "removed_inherited_strehl": removed,
            "effective_strehl": effective_strehl,
            "rayon_num_threads": int(env["RAYON_NUM_THREADS"]),
            "numeric_thread_caps": {
                name: int(env[name])
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
        },
        "arms": {"scale": scale, "crop": crop},
    }
    for name, pmax in cc.PMAX.items():
        cc.validate_provenance(
            payload,
            CROP,
            SCALE,
            pmax,
            cc.HASHES[pmax],
            cc.HASHES[cc.SCALE_MASTER],
            name,
            verify_live_source=False,
        )
    PROVENANCE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "GREEN",
                "provenance": str(PROVENANCE),
                "source_manifest": pre["digest"],
                "scale_sha256": scale["sha256"],
                "crop_sha256": crop["sha256"],
                "scale_shape": scale["shape"],
                "crop_shape": crop["shape"],
                "scale_facts": scale["facts"],
                "crop_facts": crop["facts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
