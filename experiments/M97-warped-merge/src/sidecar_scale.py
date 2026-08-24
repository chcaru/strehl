"""What sign and unit does the shipped sidecar actually carry?

The orchestrator measured, independently of all strehl code, that the SUBJECT
SHRINKS through bee-3-cpl: a feature at radius r in frame 0 sits at radius
0.85715*r in frame 298. M86's prose says the opposite ("frame 0 is roughly
10-12% smaller than frame 298"). One of them is wrong, and the disagreement is
silent: a flipped sign still renders, it just doubles the drift.

This reads the sidecar and asks it directly. A placement maps REFERENCE coords
-> that frame's coords and is applied by `gather_checked` with no inversion, so
if the reference is frame `ref` and the true subject scale of frame k is s_k,
the placement's linear part must have modulus

    |a_k| = s_k / s_ref

which DECREASES with k under the orchestrator's measurement and INCREASES with
k under M86's prose. The sidecar cannot be ambiguous about this, so it settles
which convention is in force -- without needing anyone's prose to be right.

Unit is settled the same way: |a_k| is dimensionless, but the corner
displacement |a_k - 1| * r_corner is not, so we report it on both grids.
"""

import json
import struct
import sys


def parse(path: str):
    """Parse `strehl-warpmap 1`. Returns (header, [(idx, state, a, b), ...])."""
    header, rows = {}, []
    with open(path, "r", encoding="utf-8") as fh:
        first = fh.readline().strip()
        assert first.startswith("strehl-warpmap"), first
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if not parts[0].lstrip("-").isdigit():
                header[parts[0]] = " ".join(parts[1:])
                continue
            idx, state = int(parts[0]), parts[1]
            if len(parts) >= 6:
                a_re, a_im, b_re, b_im = (
                    struct.unpack(">d", bytes.fromhex(p))[0] for p in parts[2:6]
                )
                rows.append((idx, state, complex(a_re, a_im), complex(b_re, b_im)))
            else:
                rows.append((idx, state, None, None))
    return header, rows


def main(argv: list[str]) -> int:
    path = argv[1]
    header, rows = parse(path)
    print(f"sidecar : {path}")
    for k, v in header.items():
        print(f"  {k:<14} {v}")
    placed = [r for r in rows if r[2] is not None]
    print(f"  records        {len(rows)} ({len(placed)} with a transform)")

    # The reference frame is the one whose placement is exactly the identity.
    ident = [r[0] for r in placed if abs(r[2] - 1.0) < 1e-12 and abs(r[3]) < 1e-12]
    print(f"  identity at    {ident}")

    # Plane corner radius: the sidecar is fitted on the half-res CFA quad grid.
    plane_w, plane_h = 3512.0, 2344.0
    r_plane = 0.5 * (plane_w**2 + plane_h**2) ** 0.5

    print()
    print(f"{'idx':>5} {'state':>8} {'|a|':>10} {'|b| px':>10} "
          f"{'corner px (plane)':>18} {'(sensor)':>10}")
    out = []
    for idx, state, a, b in placed:
        if idx % 20 and idx != placed[-1][0]:
            continue
        s, corner = abs(a), abs(a - 1.0) * r_plane
        print(f"{idx:>5} {state:>8} {s:>10.6f} {abs(b):>10.2f} "
              f"{corner:>18.2f} {corner * 2:>10.2f}")
        out.append(dict(idx=idx, scale=s, b=abs(b), corner_plane=corner))

    first, last = placed[0], placed[-1]
    s0, sN = abs(first[2]), abs(last[2])
    print()
    print(f"frame {first[0]} |a| = {s0:.6f}")
    print(f"frame {last[0]} |a| = {sN:.6f}")
    print(f"ratio |a_last| / |a_first| = {sN / s0:.6f}")
    print()
    if sN < s0:
        print("SIDECAR SAYS: the subject SHRINKS through the bracket")
        print("  -> agrees with the orchestrator's independent NCC measurement")
    else:
        print("SIDECAR SAYS: the subject GROWS through the bracket")
        print("  -> agrees with M86's prose, DISAGREES with the NCC measurement")
    span = abs(sN / s0 - 1.0) * r_plane
    print(f"end-to-end corner drift implied by the sidecar: "
          f"{span:.2f} plane px ({span * 2:.2f} sensor px)")

    with open(argv[2], "w", encoding="utf-8") as fh:
        json.dump(dict(path=path, header=header, r_plane=r_plane,
                       s_first=s0, s_last=sN, rows=out), fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
