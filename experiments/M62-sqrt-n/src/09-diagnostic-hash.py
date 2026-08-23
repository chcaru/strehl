"""Rule 26 -- prove the diagnostic does not perturb the output, by hash.

Arms A1 and B2 pass `--flat-roi` so the CLI prints its own invariant beside the
truth-referenced score. An argument that a reporting channel is read-only is not
evidence that it is. This runs the same merge with the diagnostic on and off and
compares SHA-256 of the written TIFF.

Uses the Arm D burst, which is already on disk.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

BURST = H.DATA / "armD"
ROI = "64,64,512,512"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    n = len(list(BURST.glob("*.arw")))
    assert n >= 2, f"{BURST}: {n} frames -- run 06-armD.py first"
    out = {}
    for gate in (0.0, 16.0):
        h = {}
        for tag, extra in (("off", []), ("on", ["--flat-roi", ROI])):
            tif = H.DATA / f"hash-{tag}-g{gate}.tif"
            H.run_cli(["merge", str(BURST), "--gate", gate] + extra + ["--out", str(tif)],
                      H.EVID / f"09-hash-{tag}-g{gate}.log")
            h[tag] = sha(tif)
            tif.unlink()
        h["identical"] = h["off"] == h["on"]
        out[f"gate{gate}"] = h
    out["frames"] = n
    out["roi"] = ROI
    assert all(v["identical"] for k, v in out.items() if k.startswith("gate")), \
        "DIAGNOSTIC PERTURBS THE OUTPUT -- rule 26 violated"
    H.dump("09-diagnostic-hash.json", out)


if __name__ == "__main__":
    main()
