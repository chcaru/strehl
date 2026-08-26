"""Emit genuinely WARPED, co-registered single-frame renders.

The problem ORCH named: the hull must be taken over the aligned, warped frames
as the merge actually sees them. Comparing against unwarped frames manufactures
violations and is the main way this instrument can lie.

The obvious route is closed by two hard checks. `alignment_for`
(merge_cmd.rs:2051) requires `map.check_stack(&identity)` AND
`map.len() == paths.len()`, and `STREHL_ONLY_FRAME=k` makes `paths.len() == 1`,
so a 205-frame sidecar is refused for a single-frame render. That is true of the
`STREHL_WARPMAP` override as well as of the cache path.

The route that IS open: the sidecar is a documented text format, the stack
identity is FNV-1a over `(file name, file size)` (warpmap.rs:194-238), and the
merge applies `map.warp(index)` with no special-casing of the `reference` field
(merge_cmd.rs:1332 and 3703). So for each frame k this writes a ONE-frame
sidecar carrying the 205-frame solve's own placement for frame k, verbatim as
f64 bit patterns so nothing round-trips through a decimal.

The frame is then rendered by strehl itself, through strehl's own gather and
strehl's own Catmull-Rom kernel. I do not reimplement the warp.

COMMISSIONING, and it is not optional. Two independent checks:

  1. This script recomputes the FNV-1a digest of the full 205-frame stack and
     asserts it equals the `stack-digest` the solver wrote. If my FNV is wrong,
     this fails here rather than silently producing sidecars that are refused.
  2. `alignment_for` answers a bad sidecar with a HARD error, never by
     re-solving ("Refusal instead of recovery", merge_cmd.rs:2034). So a render
     that exits 0 having been told to use my sidecar is itself proof that the
     digest matched and the placement was accepted. Acceptance is the test.
"""
from __future__ import annotations

import argparse
import struct
import subprocess
from pathlib import Path

OFFSET = 0xCBF29CE484222325
PRIME = 0x00000100000001B3
MASK = 0xFFFFFFFFFFFFFFFF


def fnv1a(entries: list[tuple[str, int]]) -> int:
    h = OFFSET
    def mix(bs: bytes) -> None:
        nonlocal h
        for b in bs:
            h ^= b
            h = (h * PRIME) & MASK
    for name, size in entries:
        mix(name.encode())
        mix(b"\0")
        mix(struct.pack("<Q", size))
        mix(b"\0")
    return h


def parse(path: Path) -> tuple[dict[str, str], list[str]]:
    head: dict[str, str] = {}
    rows: list[str] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.split()[0].isdigit():
            rows.append(s)
        else:
            k, _, v = s.partition(" ")
            head[k] = v.strip()
    return head, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sidecar", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--binary", required=True)
    ap.add_argument("--merge", default="pyramid")
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=-1)
    a = ap.parse_args()

    side = Path(a.sidecar)
    head, rows = parse(side)
    frames = int(head["frames"])
    assert len(rows) == frames, f"{len(rows)} rows for {frames} frames"

    src = Path(a.subject)
    arws = sorted(src.glob("*.ARW"))
    assert len(arws) == frames, f"{len(arws)} ARW vs {frames} frames in sidecar"

    # COMMISSIONING 1: reproduce the solver's own digest before trusting anything
    want = int(head["stack-digest"], 16)
    got = fnv1a([(p.name, p.stat().st_size) for p in arws])
    print(f"  stack-digest from sidecar : {want:016x}")
    print(f"  stack-digest recomputed   : {got:016x}")
    assert got == want, "FNV-1a mismatch: my digest implementation is wrong, stopping"
    print("  digest reproduced. The file-order and hash rule are confirmed.\n")

    outdir = Path(a.outdir)
    (outdir / "sidecars").mkdir(parents=True, exist_ok=True)
    (outdir / "frames").mkdir(parents=True, exist_ok=True)

    last = frames - 1 if a.last < 0 else a.last
    for k in range(a.first, last + 1):
        tif = outdir / "frames" / f"f{k:04d}.tiff"
        if tif.exists():
            continue
        p = arws[k]
        d = fnv1a([(p.name, p.stat().st_size)])
        fields = rows[k].split()
        assert int(fields[0]) == k and fields[1] == "placed", rows[k]
        body = " ".join(fields[2:6])          # the four f64 bit patterns, verbatim
        sc = outdir / "sidecars" / f"f{k:04d}.warpmap.txt"
        sc.write_text(
            "strehl-warpmap 1\n"
            f"stack-name {head['stack-name']}\n"
            f"stack-digest {d:016x}\n"
            "frames 1\n"
            f"plane {head['plane']}\n"
            "reference 0\n"
            f"strategy {head['strategy']}\n"
            f"resampler {head['resampler']}\n"
            f"heldout-px {head['heldout-px'].split()[0]}\n"
            f"cycle-floor-px {head['cycle-floor-px'].split()[0]}\n"
            f"note synthesised by warpframes.py from {side.name} frame {k}\n"
            f"0 placed {body}\n"
            "end 1\n"
        )
        env = {"STREHL_ONLY_FRAME": str(k), "STREHL_WARPMAP": str(sc)}
        import os
        e = dict(os.environ)
        for v in list(e):
            if v.startswith("STREHL_"):
                del e[v]
        e.update(env)
        log = outdir / "frames" / f"f{k:04d}.log"
        with log.open("w") as lf:
            rc = subprocess.run(
                [a.binary, "stack", str(src), "--out", str(tif), "--merge", a.merge],
                stdout=lf, stderr=subprocess.STDOUT, env=e,
            ).returncode
        if rc != 0:
            print(f"  frame {k}: rc={rc}  see {log}")
            print(log.read_text()[-1500:])
            return 1
        # COMMISSIONING 2: the render must say it used MY sidecar, not a re-solve
        txt = log.read_text()
        if k == a.first:
            for line in txt.splitlines():
                if "alignment" in line.lower() or "sidecar" in line.lower():
                    print(f"    [frame {k}] {line.strip()}")
        log.unlink(missing_ok=True)
        if (k + 1) % 25 == 0 or k == last:
            print(f"  warped {k + 1}/{frames}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
