"""Warpmap -> per-site sample phases, for M-PHASE0-PHASE's census.

`plib.py` deliberately reads no data file: it is pure algebra.  This module is
the other half -- it turns the product's own cached alignment sidecars into the
displacement multiset `{d_i}` that `plib.kappa` consumes.

Everything here is pinned to primary source, not inferred:

  DIRECTION   `crates/strehl-core/src/warpmap.rs:155` documents `FrameWarp::Placed`
              as "its placement, reference -> frame", and `warpmap.rs:460-470`
              proves it by construction: for each *destination* (reference) pixel
              it evaluates `t.apply_at(px, py, cx, cy)` and samples the *source
              frame* there.  So `t` carries reference coordinates into frame
              coordinates.

  CENTRE      `cx = width as f64 * 0.5`, unanimous across the crate:
              `align.rs:382`, `align.rs:1289`, `align.rs:2916`,
              `warpmap.rs:460`, `align_cmd.rs:2081`, `align_cmd.rs:2584`.
              No `(W-1)/2` convention exists anywhere in the product.

  FIELD ORDER `warpmap.rs:651-654` writes `a.re a.im b.re b.im` as f64 bit
              patterns; the trailing decimals are a human aid and are re-derived
              here as a parse check, never parsed.

  UNITS       The warp plane is 3516x2344 against a 7032x4688 rawler active
              area, so **1 plane px = 2 sensor px**.  The alias lattices live on
              the *sensor* grid, so the fractional part must be taken in sensor
              units.  `frac(2 t(p))` and `2 frac(t(p))` are different numbers and
              only the first is right; `c_units_are_not_interchangeable` fails if
              this is ever swapped.
"""

import math
import os
import re
import struct

import numpy as np

WARPMAP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "strehl", "warpmaps")

PLANE_TO_SENSOR = 2.0

# The exact `1/a` term in `site_phases`. Only `p2_controls.py` ever turns this
# off, to prove control C-U can actually see its absence.
A_CORRECTION = True

_HEX = re.compile(r"^[0-9a-f]{16}$")


def _f64(h):
    """Decode one 16-hex-digit IEEE-754 big-endian bit pattern."""
    if not _HEX.match(h):
        raise ValueError("not an f64 bit pattern: %r" % (h,))
    return struct.unpack(">d", bytes.fromhex(h))[0]


def parse_warpmap(path):
    """Parse a `strehl-warpmap 1` sidecar into a plain dict.

    Returns keys: stack_name, stack_digest, frames, plane (w, h), reference,
    strategy, resampler, placements (list of None-or-(a, b) complex pairs),
    refusals (list of (index, reason)), and `aid` (the printed decimals, kept
    only so the parse can be checked against them).
    """
    out = dict(path=path, placements=[], refusals=[], aid={}, header={})
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or not lines[0].startswith("strehl-warpmap 1"):
        raise ValueError("not a strehl-warpmap 1 file: %s" % path)

    n = None
    for ln in lines[1:]:
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        key = parts[0]
        if key in ("stack-name", "stack-digest", "reference", "strategy",
                   "resampler", "heldout-px", "cycle-floor-px", "note"):
            out["header"][key] = " ".join(parts[1:])
        elif key == "frames":
            n = int(parts[1])
            out["frames"] = n
            out["placements"] = [None] * n
        elif key == "plane":
            w, h = parts[1].split("x")
            out["plane"] = (int(w), int(h))
        elif key.isdigit():
            i = int(key)
            state = parts[1]
            if state == "placed":
                a = complex(_f64(parts[2]), _f64(parts[3]))
                b = complex(_f64(parts[4]), _f64(parts[5]))
                out["placements"][i] = (a, b)
                if "#" in ln:
                    out["aid"][i] = ln.split("#", 1)[1].strip()
            elif state == "refused":
                out["refusals"].append((i, " ".join(parts[2:])))
            else:
                raise ValueError("unknown frame state %r in %s" % (state, path))
    out["stack_name"] = out["header"].get("stack-name")
    out["stack_digest"] = out["header"].get("stack-digest")
    out["reference_index"] = int(out["header"]["reference"]) if "reference" in out["header"] else None
    out["placed_count"] = sum(1 for p in out["placements"] if p is not None)
    return out


def aid_values(s):
    """Pull `g=`, `rot=`, `dx=`, `dy=` out of a printed human-aid comment.

    Rust's `{:e}` writes the exponent with no `+` and no zero padding (`e0`,
    `e1`, `e-2`), so the sign is optional in this pattern.
    """
    d = {}
    for k in ("g", "rot", "dx", "dy"):
        m = re.search(r"\b%s=([+-][0-9.]+(?:e[+-]?[0-9]+)?)" % k, s)
        if m:
            d[k] = float(m.group(1))
    return d


def apply_at(a, b, x, y, cx, cy):
    """`Similarity::apply_at` from `align.rs:290`, in plane coordinates."""
    q = a * complex(x - cx, y - cy) + b
    return q.real + cx, q.imag + cy


def frac_centred(v):
    """`v - round(v)`, the signed offset to the nearest lattice point."""
    return v - np.round(v)


def site_offset(a, b, plane, px, py):
    """Offset from reference site `(px, py)` to frame `(a, b)`'s nearest sample.

    Returned in **frame** sensor coordinates, before the `1/a` change of basis.
    Each component is a `v - round(v)`, so `|e_x|, |e_y| <= 0.5` EXACTLY, with
    no tolerance -- that bound is what control C-T tests, and it is the sharpest
    statement the geometry supports.
    """
    w, h = plane
    sx, sy = apply_at(a, b, px, py, w * 0.5, h * 0.5)
    s = complex(sx, sy) * PLANE_TO_SENSOR
    return complex(frac_centred(s.real), frac_centred(s.imag))


def site_phases(placements, plane, px, py, frames=None):
    """Sample-lattice displacements at reference site `(px, py)`, in SENSOR px.

    Frame `i` samples the scene on the integer *sensor* grid of frame `i`.  The
    reference site `(px, py)` lands at `s = 2 t_i(p)` in that grid, so the
    nearest frame sample sits `-frac(s)` away in frame coordinates.  Carrying
    that back to reference coordinates divides by `a_i`, because
    `t^-1(q) - t^-1(t(p)) = (q - t(p)) / a`.

    The `1/a` factor is a genuine term, not a nicety -- `|a-1|` reaches ~1e-2 on
    these stacks -- but it is bounded by `|frac| * |1/a - 1| <= 0.71 * 1e-2`, so
    it moves a phase by at most ~0.007 sensor px.  It is applied exactly anyway.

    Returns `(idx, d)` where `d` is `(k, 2)` float64 in sensor px, and `idx` are
    the frame indices actually used (unplaced frames are dropped, and the caller
    is required to report how many).
    """
    idx, ds = [], []
    order = range(len(placements)) if frames is None else frames
    for i in order:
        p = placements[i]
        if p is None:
            continue
        a, b = p
        e = site_offset(a, b, plane, px, py)
        d = (-e / a) if A_CORRECTION else (-e)
        idx.append(i)
        ds.append((d.real, d.imag))
    return np.array(idx, dtype=int), np.array(ds, dtype=float).reshape(-1, 2)


def site_offsets(placements, plane, px, py, frames=None):
    """Every placed frame's raw `e`, for the exactness check in C-T."""
    w, h = plane
    out = []
    order = range(len(placements)) if frames is None else frames
    for i in order:
        p = placements[i]
        if p is None:
            continue
        a, b = p
        e = site_offset(a, b, plane, px, py)
        out.append((e.real, e.imag))
    return np.array(out, dtype=float).reshape(-1, 2)


def site_offset_wrong_units(a, b, plane, px, py):
    """The unit error this module exists to prevent: `2 frac(t(p))`.

    Not used by the census.  Present so `p2_controls.py` can demonstrate that
    the two are different numbers, rather than merely asserting it.  It is
    falsified by arithmetic: it can return more than half a period, and an
    offset to the NEAREST lattice point cannot.
    """
    w, h = plane
    sx, sy = apply_at(a, b, px, py, w * 0.5, h * 0.5)
    return complex(frac_centred(sx), frac_centred(sy)) * PLANE_TO_SENSOR


def site_phases_wrong_units(placements, plane, px, py, frames=None):
    idx, ds = [], []
    order = range(len(placements)) if frames is None else frames
    for i in order:
        p = placements[i]
        if p is None:
            continue
        a, b = p
        e = site_offset_wrong_units(a, b, plane, px, py)
        d = (-e / a) if A_CORRECTION else (-e)
        idx.append(i)
        ds.append((d.real, d.imag))
    return np.array(idx, dtype=int), np.array(ds, dtype=float).reshape(-1, 2)


def list_maps(directory=None):
    """Every cached sidecar, grouped by stack name."""
    directory = directory or WARPMAP_DIR
    by_stack = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".warpmap.txt"):
            continue
        stack = name.split("-", 1)[0]
        by_stack.setdefault(stack, []).append(os.path.join(directory, name))
    return by_stack
