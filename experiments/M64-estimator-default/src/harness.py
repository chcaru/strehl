"""Shared harness: constants, burst generation, and the truth-referenced statistic.

Every sensor constant here is READ FROM the shipped crate rather than retyped:
see `constants()` for the parse of `crates/strehl-core/src/profile.rs`.

**Nothing here is bound to the binary M62 measured.** The executable under test
comes from `$STREHL_BIN` (default: the working tree's release build) and the
constants from `$STREHL_SRC` (default: the repo). `provenance()` records the
binary's sha256, the repo HEAD and whether `crates/` was dirty, so a reader can
tell what was actually run without taking anyone's word for it.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dngwrite import write_cfa_dng  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BUILD = ROOT / "build-head"


def _pick(env, *candidates):
    """First existing path among `$env` then `candidates`. Never silently empty."""
    v = os.environ.get(env)
    if v:
        p = pathlib.Path(v).expanduser().resolve()
        assert p.exists(), f"${env} = {p} does not exist"
        return p
    for c in candidates:
        if c.exists():
            return c
    raise AssertionError(f"none of {[str(c) for c in candidates]} exist; set ${env}")


def binary():
    """The `strehl` executable under test.

    Override with `$STREHL_BIN`. Defaults to the working tree's release build,
    then to the `build-head/` archive export M62 used when the tree would not
    compile. Nothing here is specific to the binary M62 measured.
    """
    return _pick(
        "STREHL_BIN",
        REPO / "target" / "release" / "strehl.exe",
        BUILD / "target" / "release" / "strehl.exe",
    )


def src_root():
    """The crate tree the sensor constants are parsed from.

    Override with `$STREHL_SRC`. **Must correspond to the binary under test** --
    the harness compares its own model against the binary's, and a mismatch
    would compare two different profiles. `provenance()` records both so a
    reader can check.
    """
    return _pick("STREHL_SRC", REPO, BUILD)


def provenance():
    """Where the binary and the constants actually came from, for the record."""
    exe, src = binary(), src_root()
    try:
        sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "crates"],
                               capture_output=True, text=True).stdout.strip()
    except Exception:
        sha, dirty = "unknown", "unknown"
    return dict(
        binary=str(exe),
        binary_mtime=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(exe.stat().st_mtime)),
        binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        constants_from=str(src),
        repo_head=sha,
        crates_dirty=bool(dirty),
        crates_dirty_files=dirty.splitlines() if dirty else [],
    )


DATA = ROOT / "data"
EVID = ROOT / "out"

ISO = 160.0
CONTAINER_MAX = 16383
# Plane-coordinate inset for every measured ROI. The selection window is
# WINDOW_RADIUS = 13 and the regulariser radius 8, so the combined support is
# 21 plane px; 32 leaves margin and keeps every measured pixel interior.
INSET = 32


def constants(iso=ISO):
    """Sensor constants, parsed out of the crate tree matching the binary."""
    src = (src_root() / "crates" / "strehl-core" / "src" / "profile.rs").read_text(encoding="utf-8")
    block = src[src.index("const A7C2: CameraProfile"):]
    block = block[: block.index("};")]

    def f(name):
        m = re.search(rf"{name}:\s*([0-9.]+)", block)
        assert m, f"{name} not found in A7C2 profile block"
        return float(m.group(1))

    gain_divisor = f("gain_divisor")
    base_iso = f("base_iso")
    rn_low = f("read_noise_e_low")
    rn_high = f("read_noise_e_high")
    second_base = f("second_base_iso")

    # Levels: the doc comment on `Levels::white` and the profile tests both name
    # 512 / 15360. Confirm the numbers appear in noise.rs rather than assuming.
    nsrc = (src_root() / "crates" / "strehl-core" / "src" / "noise.rs").read_text(encoding="utf-8")
    assert "black: 512.0" in nsrc and "white: 15360.0" in nsrc

    g = max(iso, base_iso) / gain_divisor
    rn_e = rn_high if iso >= second_base else rn_low
    return dict(
        gain_divisor=gain_divisor,
        base_iso=base_iso,
        read_noise_e_low=rn_low,
        read_noise_e_high=rn_high,
        second_base_iso=second_base,
        iso=iso,
        gain_dn_per_e=g,
        read_noise_e=rn_e,
        read_noise_dn=rn_e * g,
        black=512.0,
        white=15360.0,
    )


def sigma_dn(signal_dn, k):
    """`sigma(S) = sqrt(g*S + (RN_e*g)^2)`, exactly `PlaneNoise::variance`."""
    s = np.maximum(signal_dn, 0.0)
    return np.sqrt(k["gain_dn_per_e"] * s + k["read_noise_dn"] ** 2)


# --------------------------------------------------------------------------
# burst


def make_burst(latent, n, seed, outdir, k):
    """Write `n` noisy realisations of `latent` as DNG-in-.arw. Returns a report."""
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("*.arw"):
        old.unlink()
    sig = sigma_dn(latent - k["black"], k)
    clipped = 0
    for i in range(n):
        rng = np.random.default_rng([seed, i])
        y = latent + rng.normal(0.0, 1.0, latent.shape) * sig
        yr = np.rint(y)
        clipped += int((yr < 0).sum() + (yr > CONTAINER_MAX).sum())
        yq = np.clip(yr, 0, CONTAINER_MAX).astype(np.uint16)
        write_cfa_dng(outdir / f"burst{i:04d}.arw", yq, iso=int(ISO), exposure_s=1.0)
    return dict(
        n=n,
        seed=seed,
        dir=str(outdir),
        sigma_mean_dn=float(sig.mean()),
        sigma_min_dn=float(sig.min()),
        sigma_max_dn=float(sig.max()),
        clipped_samples=clipped,
    )


def read_cfa(path, shape):
    """Read back the CFA plane of a DNG written by `dngwrite`.

    The image strip is written last, so the final `h*w` u16 samples are it. This
    reads exactly the bytes handed to the CLI -- no regeneration, no seed replay.
    """
    h, w = shape
    a = np.fromfile(path, dtype="<u2")
    return a[-(h * w):].reshape(h, w).astype(np.float64)


def green(cfa):
    """`(G1 + G2) / 2` at plane resolution, in RAW DN, exactly as the merge does.

    RGGB: G1 at (even row, odd col), G2 at (odd row, even col) -- matching
    `CfaPlane::rggb_offset` in `crates/strehl-core/src/plane.rs`.
    """
    return 0.5 * (cfa[0::2, 1::2] + cfa[1::2, 0::2])


def read_tiff_green(path, k):
    """Green channel of a CLI-written linear 16-bit RGB TIFF, back in raw DN.

    `write_merged` encodes `v = clamp((raw - black) * gain / range, 0, 1)` then
    `(v * 65535 + 0.5) as u16`. The green gain is exactly 1.0 (white balance
    normalises green to unity), so green -- and only green -- inverts cleanly.
    """
    import tifffile

    img = tifffile.imread(str(path))
    assert img.dtype == np.uint16 and img.ndim == 3 and img.shape[2] == 3, (img.dtype, img.shape)
    g = img[:, :, 1].astype(np.float64)
    return g / 65535.0 * (k["white"] - k["black"]) + k["black"]


# --------------------------------------------------------------------------
# statistic


def roi(a, inset=INSET):
    return a[inset:-inset, inset:-inset]


def ratio_and_se(merged_g, truth_g, single_resid_ms, block=64, rng_seed=7):
    """Noise-reduction ratio, truth-referenced, with a block-bootstrap SE.

    `merged_g`, `truth_g` are plane-resolution green in raw DN over the ROI.
    `single_resid_ms` is the per-pixel MEAN SQUARE residual of a single frame
    against truth, pooled over ALL frames, on the same ROI grid -- so no one
    frame is a privileged denominator (fact 441).
    """
    r = merged_g - truth_g
    h, w = r.shape
    nb_y, nb_x = h // block, w // block
    r2 = r[: nb_y * block, : nb_x * block].reshape(nb_y, block, nb_x, block)
    s2 = single_resid_ms[: nb_y * block, : nb_x * block].reshape(nb_y, block, nb_x, block)
    num_blocks = s2.mean(axis=(1, 3)).ravel()  # single-frame MS per block
    den_blocks = (r2**2).mean(axis=(1, 3)).ravel()  # merged MS per block

    point = float(np.sqrt(num_blocks.mean() / den_blocks.mean()))
    rng = np.random.default_rng(rng_seed)
    nb = num_blocks.size
    draws = np.empty(2000)
    for b in range(draws.size):
        idx = rng.integers(0, nb, nb)
        draws[b] = np.sqrt(num_blocks[idx].mean() / den_blocks[idx].mean())
    return point, float(draws.std(ddof=1))


def run_cli(args, log_path, check=True):
    """Run the binary under test. Returns stdout+stderr, or `None` if it refused.

    `check=False` lets an arm probe an invocation the binary may not support --
    an UNSUPPORTED arm is a result, not a crash.
    """
    cmd = [str(binary())] + [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "$ " + " ".join(cmd) + f"\n\n[exit {p.returncode}]\n--- stdout ---\n" + p.stdout
        + "\n--- stderr ---\n" + p.stderr,
        encoding="utf-8",
    )
    if p.returncode != 0:
        if not check:
            return None
        raise AssertionError(f"{' '.join(cmd)} exited {p.returncode}\n{p.stderr[-4000:]}")
    return p.stdout + "\n" + p.stderr


def grep1(text, pattern, cast=float):
    m = re.search(pattern, text)
    assert m, f"pattern not found: {pattern}"
    return cast(m.group(1))


def dump(name, obj):
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print(json.dumps(obj, indent=2))
