"""Run M80's repaired invariant on M77's exact B1/B2 ROIs."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent / "out"
BIN = HERE.parent / "target-m80" / "release" / "strehl.exe"
M77_OUT = ROOT / "experiments" / "M77-gate-sweep" / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACKS = ("wrapped-text-1", "wrapped-text-2")
LADDER = (0, 2, 4, 8, 16, 24, 32, 40, 48, 64, 96, 128)


def roi_arg(roi: dict) -> str:
    return f"{roi['x']},{roi['y']},{roi['w']},{roi['h']}"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if not BIN.exists():
        raise SystemExit(f"private binary does not exist: {BIN}")
    OUT.mkdir(parents=True, exist_ok=True)
    rois = json.loads((M77_OUT / "01-rois.json").read_text(encoding="utf-8"))
    rois.update(
        json.loads((M77_OUT / "06-roi-wt2.json").read_text(encoding="utf-8"))
    )
    summary = {
        "binary": str(BIN.relative_to(ROOT)),
        "binary_sha256": sha256(BIN),
        "ladder": list(LADDER),
        "runs": [],
    }
    print(f"MEASURED: binary={BIN} sha256={summary['binary_sha256']}")
    for stack in STACKS:
        r = rois[stack]
        for tag, detail in (("B2", r["flat_roi"]), ("B1", r["detail_roi"])):
            cmd = [
                str(BIN),
                "stack",
                str(CORPUS / stack),
                "--gate",
                *[str(g) for g in LADDER],
                "--flat-roi",
                roi_arg(r["flat_roi"]),
                "--detail-roi",
                roi_arg(detail),
            ]
            print(f"MEASURED: start {stack}/{tag}")
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
            log = OUT / f"03-{tag}-{stack}.log"
            log.write_text(p.stdout, encoding="utf-8")
            row = {
                "stack": stack,
                "arm": tag,
                "flat_roi": r["flat_roi"],
                "detail_roi": detail,
                "exit": p.returncode,
                "seconds": elapsed,
                "log": str(log.relative_to(ROOT)),
            }
            summary["runs"].append(row)
            print(
                f"MEASURED: finish {stack}/{tag} exit={p.returncode} "
                f"seconds={elapsed:.3f} log={log.relative_to(ROOT)}"
            )
            if p.returncode != 0:
                print(p.stdout[-4000:])
                (OUT / "03-run-real.json").write_text(
                    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
                )
                raise SystemExit(f"{stack}/{tag} exited {p.returncode}")
    (OUT / "03-run-real.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
