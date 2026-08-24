"""Build planted warp sidecars from a solved one.

The sidecar is inspectable text, so every control M97 needs is a file
transformation and needs no change to the solver:

  identity  every placement replaced by the identity -> the placebo
  jitter    a known pseudo-random translation added to every placement's
            translation part -> the positive control, which must make a
            geometry metric worse
  scale     a known extra magnification ramp across the stack

Only the translation part `b` is perturbed for `jitter`. That is deliberate:
adding to `b` is a per-frame translation of where the gather samples from, and
its meaning does not depend on which way round the rotation/scale convention
runs, so the plant cannot be silently misinterpreted the way an `a`-side plant
could.

Usage:
  sidecar_tool.py identity <in> <out>
  sidecar_tool.py jitter   <in> <out> <sigma_px> <seed>
  sidecar_tool.py refuse   <in> <out> <every_nth>
"""

import struct
import sys


def f2h(x: float) -> str:
    return struct.pack(">d", x).hex()


def h2f(h: str) -> float:
    return struct.unpack(">d", bytes.fromhex(h))[0]


def load(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", newline="\n") as fh:
        return fh.read().split("\n")


def save(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def is_record(line: str) -> bool:
    parts = line.split()
    return len(parts) >= 6 and parts[0].isdigit() and parts[1] in ("placed", "refused")


def main() -> None:
    mode, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    lines = load(src)
    out: list[str] = []
    n_touched = 0
    # A tiny self-contained LCG, so the plant is exactly reproducible and does
    # not depend on any numpy/random version.
    state = int(sys.argv[5]) if mode == "jitter" else 0
    sigma = float(sys.argv[4]) if mode == "jitter" else 0.0
    every = int(sys.argv[4]) if mode == "refuse" else 0
    planted: list[tuple[int, float, float]] = []

    def nxt() -> float:
        """Uniform in [-1, 1) from a 64-bit LCG."""
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return ((state >> 11) / float(1 << 53)) * 2.0 - 1.0

    for line in lines:
        if not is_record(line):
            out.append(line)
            continue
        parts = line.split()
        idx = int(parts[0])
        if mode == "identity":
            out.append(f"{idx} placed {f2h(1.0)} {f2h(0.0)} {f2h(0.0)} {f2h(0.0)} # identity")
            n_touched += 1
        elif mode == "jitter":
            if parts[1] != "placed":
                out.append(line)
                continue
            a_re, a_im = parts[2], parts[3]
            b_re, b_im = h2f(parts[4]), h2f(parts[5])
            # Two uniforms scaled so the per-axis sd is `sigma`.
            jx, jy = nxt() * sigma * (3.0**0.5), nxt() * sigma * (3.0**0.5)
            planted.append((idx, jx, jy))
            out.append(
                f"{idx} placed {a_re} {a_im} {f2h(b_re + jx)} {f2h(b_im + jy)}"
                f" # jitter dx={jx:+.4f} dy={jy:+.4f}"
            )
            n_touched += 1
        elif mode == "refuse":
            if idx % every == 0 and parts[1] == "placed":
                out.append(f"{idx} refused planted-refusal-M97")
                n_touched += 1
            else:
                out.append(line)
        else:
            raise SystemExit(f"unknown mode {mode}")

    save(dst, out)
    print(f"mode={mode} src={src} dst={dst} records touched={n_touched}")
    if planted:
        xs = [p[1] for p in planted]
        ys = [p[2] for p in planted]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sx = (sum((v - mx) ** 2 for v in xs) / n) ** 0.5
        sy = (sum((v - my) ** 2 for v in ys) / n) ** 0.5
        rms = (sum(x * x + y * y for x, y in zip(xs, ys)) / n) ** 0.5
        print(f"  planted jitter: sd_x={sx:.4f} sd_y={sy:.4f} rms_disp={rms:.4f} px (plane)")
        print(f"  max |dx|={max(abs(v) for v in xs):.4f}  max |dy|={max(abs(v) for v in ys):.4f}")


if __name__ == "__main__":
    main()
