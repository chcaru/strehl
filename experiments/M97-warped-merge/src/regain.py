"""Rewrite a sidecar with a scalar gain applied to every placement.

This does NOT touch the estimator, and it is not a fix. It is a probe: M97
measured that the shipped solve applies only 54.3% of the drift that is
actually present on bee-3-cpl, and the open question that measurement left is
whether correcting the gain makes the PHOTOGRAPH better or merely makes the
geometry number better. Feeding a re-gained sidecar through STREHL_WARPMAP
answers that end to end, through the real renderer, with no code change.

Scale composes multiplicatively along a chain of frames, so an estimator that
attenuates each pairwise log-scale by a constant yields a global solve whose
log-scale is attenuated by the same constant. The correction is therefore
applied in the log, a' = exp(g * ln a). Translation composes additively along
the chain, so b is scaled linearly.

The gain is EMPIRICAL AND PER-STACK -- 1.9083 is ln(0.85714)/ln(0.92241)
measured on bee-3-cpl frames 0 and 298. It is not a universal constant and
must not be shipped as one.

The stack digest and every header line are copied verbatim, so the result still
passes `check_stack` and can only be applied to the bracket it was fitted on.
"""

import struct
import sys


def hexf(x: float) -> str:
    return struct.pack(">d", x).hex()


def unhexf(s: str) -> float:
    return struct.unpack(">d", bytes.fromhex(s))[0]


def main(argv: list[str]) -> int:
    src, dst, gain = argv[1], argv[2], float(argv[3])
    n_placed = n_other = 0
    out = []
    with open(src, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    for line in lines:
        body = line.split("#", 1)[0].strip()
        parts = body.split()
        if len(parts) >= 6 and parts[0].lstrip("-").isdigit():
            idx, state = parts[0], parts[1]
            a = complex(unhexf(parts[2]), unhexf(parts[3]))
            b = complex(unhexf(parts[4]), unhexf(parts[5]))
            if a != 0:
                # log-scale gain; identity is a fixed point, so gain 1.0 and
                # any identity placement are both exactly preserved.
                a = complex(pow(a, gain))
            b = b * gain
            out.append(
                f"{idx} {state} {hexf(a.real)} {hexf(a.imag)} "
                f"{hexf(b.real)} {hexf(b.imag)} "
                f"# |a|={abs(a):.6f} |b|={abs(b):.2f} gain={gain:g}"
            )
            n_placed += 1
        else:
            out.append(line)
            n_other += 1

    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"gain {gain:g}: rewrote {n_placed} placements, copied {n_other} other lines")
    print(f"  {src}\n  -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
