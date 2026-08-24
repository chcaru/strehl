"""Prove the repaired observer cannot move the written merge."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent / "out"
WORK = HERE.parent / "control-work"
BIN = HERE.parent / "target-m80" / "release" / "strehl.exe"
STACK = pathlib.Path(r"D:\personal\macro\109MSDCF")
M77_ROIS = ROOT / "experiments" / "M77-gate-sweep" / "out" / "01-rois.json"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def roi_arg(roi: dict) -> str:
    return f"{roi['x']},{roi['y']},{roi['w']},{roi['h']}"


def run(label: str, path: pathlib.Path, extra: list[str]) -> dict:
    cmd = [
        str(BIN),
        "stack",
        str(STACK),
        "--gate",
        "4",
        "--out",
        str(path),
        *extra,
    ]
    started = time.perf_counter()
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter() - started
    (OUT / f"05-{label}.log").write_text(p.stdout, encoding="utf-8")
    if p.returncode != 0 or not path.exists():
        raise RuntimeError(f"{label} exit={p.returncode} exists={path.exists()}")
    return {
        "label": label,
        "exit": p.returncode,
        "seconds": elapsed,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    no_roi = WORK / "05-no-roi.tif"
    with_roi = WORK / "05-with-roi.tif"
    for path in (no_roi, with_roi):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite stale output: {path}")
    rois = json.loads(M77_ROIS.read_text(encoding="utf-8"))["109MSDCF"]
    try:
        a = run("no-roi", no_roi, [])
        b = run(
            "with-roi",
            with_roi,
            [
                "--flat-roi",
                roi_arg(rois["flat_roi"]),
                "--detail-roi",
                roi_arg(rois["detail_roi"]),
            ],
        )
        identical = a["bytes"] == b["bytes"] and a["sha256"] == b["sha256"]
        result = {"without_observer": a, "with_observer": b, "identical": identical}
        (OUT / "05-nonperturbation.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        text = (
            f"MEASURED: no ROI exit={a['exit']} seconds={a['seconds']:.3f} "
            f"bytes={a['bytes']} sha256={a['sha256']}\n"
            f"MEASURED: with ROI exit={b['exit']} seconds={b['seconds']:.3f} "
            f"bytes={b['bytes']} sha256={b['sha256']}\n"
            f"MEASURED: byte-identical={identical}\n"
        )
        (OUT / "05-nonperturbation.log").write_text(text, encoding="utf-8")
        print(text, end="")
        if not identical:
            raise SystemExit("M80 observer changed the merged output")
    finally:
        for path in (no_roi, with_roi):
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
