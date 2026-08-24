#!/usr/bin/env python3
"""Build a POISONED warp sidecar for M111's cache-contamination control.

Fact 1446: `StackIdentity` keys the frame set but not `reference` and not
`resampler`, so a differently-configured solve of the same frames passes
`check_stack` and is served from cache under an identical command line.

The poison this writes is the *effect* of that defect made explicit: a sidecar
that is accepted by every identity check strehl performs -- same stack name,
same digest, same frame count, same plane -- and that places the frames
somewhere else. If the renderer reads it, the output bytes move. If the output
bytes do not move when this file is substituted, the substitution is inert and
any "CLEAN" verdict resting on it is worthless (discipline 722).

The perturbation is +DX_PX plane pixels of horizontal translation on every
frame except the reference. It is deliberately NOT a uniform shift of all
frames: shifting every frame equally would translate the whole render and could
be mistaken for a crop, whereas leaving the reference alone is a genuine change
of *registration* -- the frames no longer land on each other.

`b_re` is the real part of the translation term, stored as an f64 bit pattern.
The trailing `# g=... dx=...` comment is documented as a human aid that is NOT
parsed, so it is rewritten only to keep the file honest to a reader.
"""

import struct
import sys
from pathlib import Path

DX_PX = 2.0


def bits_to_f64(tok: str) -> float:
    return struct.unpack(">d", bytes.fromhex(tok))[0]


def f64_to_bits(x: float) -> str:
    return struct.pack(">d", x).hex()


def poison(src: Path, dst: Path, dx_px: float = DX_PX) -> int:
    lines = src.read_text(encoding="utf-8").splitlines()
    reference = None
    out = []
    touched = 0
    for line in lines:
        if line.startswith("reference "):
            reference = int(line.split()[1])
        # Header, comment and blank lines pass through untouched.
        if not line or line.startswith("#") or not line[0].isdigit():
            out.append(line)
            continue
        parts = line.split()
        idx, state = int(parts[0]), parts[1]
        if state != "placed" or idx == reference:
            out.append(line)
            continue
        a_re, a_im, b_re, b_im = (bits_to_f64(t) for t in parts[2:6])
        b_re += dx_px
        touched += 1
        out.append(
            "%d %s %s %s %s %s # POISONED dx%+.4f" % (
                idx, state,
                f64_to_bits(a_re), f64_to_bits(a_im),
                f64_to_bits(b_re), f64_to_bits(b_im),
                dx_px,
            )
        )
    if reference is None:
        raise SystemExit("MUTATION TARGET NOT FOUND: no 'reference' line in %s" % src)
    if touched == 0:
        raise SystemExit("MUTATION TARGET NOT FOUND: 0 placed frames rewritten in %s" % src)
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    return touched


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    n = poison(src, dst)
    print("poisoned %d frames by %+0.1f plane px -> %s" % (n, DX_PX, dst))
