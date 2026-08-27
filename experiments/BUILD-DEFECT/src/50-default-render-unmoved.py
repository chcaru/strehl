"""50-default-render-unmoved.py -- does the exposure fix move the default render?

WHAT IS BEING ESTABLISHED, AND WHY A REBUILD A/B RATHER THAN A REUSE OF ARM B
============================================================================
The fix adds `* dev.exposure_gain` to the one line in `develop_pixel` that
applies the tone gain, and wires `--exposure` through to it. ORCH's fourth
requirement is that a render with NO exposure flag must be byte-identical to
what shipped, because that is what protects the 26 delivered masters from
being silently restyled.

There is an argument that it must be: `AppliedExposure::gain()` is
`stops.exp2()`, IEEE-754 requires `exp2(0)` to be exactly `1.0`, and `x * 1.0`
is `x` bit-for-bit. **That is an argument, not a measurement**, and this
project's standing rule is that nothing is true until measured.

The obvious cheap measurement -- compare against `47-expo/B-plain.tif`, which
is already on disk -- IS NOT VALID. Those arms were rendered from a dedicated
worktree pinned at 7c3df34d. HEAD has moved many times since under other
lanes. A byte difference across that gap would be unattributable: it could be
my exposure change or it could be any of eight other agents' commits. **A
control that cannot attribute its own result is not a control.**

So this builds BOTH arms from the same tree, in the same session, differing
ONLY in the two files this lane owns:

  baseline : the HEAD blobs of image_out.rs and stack.rs (i.e. the shipped
             behaviour), with every other file in the working tree left
             exactly as it is
  fixed    : the working-tree versions, i.e. baseline + the exposure fix

Every other lane's uncommitted work is present in BOTH arms and therefore
cancels. The difference between the arms is the fix and nothing else.

COMMISSIONING THE CONTROL ITSELF
--------------------------------
A swap that swaps nothing produces two identical binaries and a triumphant
"byte-identical" that means nothing at all. So before building, this asserts
the HEAD blob and the working file actually DIFFER for at least one of the two
files, and refuses if they do not. This is the same trap as a mutation test
whose mutation does not land: the green is a statement about the harness.

Restoration is unconditional (`finally`) and verified by hash against a
$env:TEMP backup taken before anything is written. The backup is never taken
with `git checkout --`, which reverts to HEAD and has destroyed uncommitted
work on this machine before.

WHAT EACH ARM IS FOR
--------------------
  B-plain   `--srgb`                    REQUIREMENT 4: must be bit-identical
  A-auto    `--srgb --auto-exposure`    must now equal B-plain exactly, since
                                        --auto-exposure becomes a declared
                                        no-op (before the fix it differed from
                                        B-plain by <=1 DN on 325,297 samples)
  C-plus3   `--srgb --exposure 3`       together with D, the delivered-gain
  D-minus3  `--srgb --exposure -3`      measurement: commanded span 64x

Pixel comparison is on the PIXELS, never on the file hash. The whole point of
this investigation was that these TIFFs carry their own banner in
`ImageDescription`, so a file hash straddles the rung between "the bytes
moved" and "the commanded quantity was delivered". For requirement 4 a file
hash is still reported -- there, "nothing whatsoever changed, including the
banner" is the actual claim -- but it is reported ALONGSIDE the pixel verdict,
never instead of it.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
OWNED = ["crates/strehl-cli/src/image_out.rs", "crates/strehl-cli/src/stack.rs"]
BIN = REPO / "target" / "release" / "strehl.exe"
STACK = r"D:\personal\macro\109MSDCF"
LIMIT = 4
OUT = Path(r"C:\dev\strehl-out\BUILD-DEFECT\50-fix")
TMP = Path(os.environ["TEMP"])

ARMS = {
    "B-plain": ["--srgb"],
    "A-auto": ["--srgb", "--auto-exposure"],
    "C-plus3": ["--srgb", "--exposure", "3"],
    "D-minus3": ["--srgb", "--exposure", "-3"],
}
ROWS = 256
FULL = 65535


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def head_blob(rel):
    """The committed bytes, read as BYTES.

    Never `git show HEAD:path > file` in PowerShell: `>` re-encodes the stream
    and has silently corrupted a comparison in this repo before.
    """
    r = subprocess.run(
        ["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True
    )
    if r.returncode != 0:
        sys.exit(f"git show HEAD:{rel} failed: {r.stderr.decode(errors='replace')}")
    return r.stdout


def build(tag):
    r = subprocess.run(
        ["cargo", "build", "--release", "-p", "strehl-cli"],
        cwd=REPO,
        capture_output=True,
    )
    if r.returncode != 0:
        sys.exit(
            f"[{tag}] cargo build failed:\n"
            + r.stderr.decode(errors="replace")[-4000:]
        )
    print(f"  [{tag}] built ok, binary sha16 {sha256(BIN)[:16]}")
    return sha256(BIN)


def render(tag, name, flags):
    out = OUT / f"{name}.{tag}.tif"
    log = OUT / f"{name}.{tag}.log"
    if out.exists():
        out.unlink()
    r = subprocess.run(
        [str(BIN), "stack", STACK, "--limit", str(LIMIT), *flags, "--out", str(out)],
        cwd=REPO,
        capture_output=True,
    )
    log.write_bytes(r.stdout + r.stderr)
    if not out.exists():
        sys.exit(
            f"[{tag}] arm {name} produced no output (exit {r.returncode}); see {log}"
        )
    return out


def pixel_verdict(pa, pb):
    """Differing-sample count, max |delta| in DN, and the LSQ slope of b on a."""
    a = tifffile.memmap(str(pa), mode="r")
    b = tifffile.memmap(str(pb), mode="r")
    if a.shape != b.shape:
        sys.exit(f"shape mismatch {a.shape} vs {b.shape}")
    diff = 0
    maxd = 0
    total = 0
    sxx = sxy = syy = 0.0
    n = 0
    for r0 in range(0, a.shape[0], ROWS):
        x = np.asarray(a[r0 : r0 + ROWS], dtype=np.int64)
        y = np.asarray(b[r0 : r0 + ROWS], dtype=np.int64)
        d = np.abs(y - x)
        diff += int(np.count_nonzero(d))
        maxd = max(maxd, int(d.max()) if d.size else 0)
        total += int(x.size)
        keep = (x < FULL) & (y < FULL)
        xf = x[keep].astype(np.float64)
        yf = y[keep].astype(np.float64)
        sxx += float(xf @ xf)
        sxy += float(xf @ yf)
        syy += float(yf @ yf)
        n += xf.size
    slope = sxy / sxx if sxx > 0 else float("nan")
    rss = max(syy - 2.0 * slope * sxy + slope * slope * sxx, 0.0)
    se = ((rss / max(n - 1, 1)) / sxx) ** 0.5 if sxx > 0 else float("nan")
    return diff, maxd, total, slope, se, n


def run_arms(live, base):
    """Build and render both arms, restoring the owned files unconditionally."""
    backups = {}
    for rel in OWNED:
        b = TMP / (Path(rel).name + ".50bak")
        shutil.copyfile(REPO / rel, b)
        if sha256(b) != hashlib.sha256(live[rel]).hexdigest():
            sys.exit(f"backup of {rel} does not match source; refusing to proceed")
        backups[rel] = b
    print(f"\nbacked up {len(backups)} owned file(s) to {TMP}")

    try:
        for rel in OWNED:
            (REPO / rel).write_bytes(base[rel])
        print("\n-- BASELINE arm (HEAD blobs of the owned files) --")
        bsha = build("baseline")
        for name, flags in ARMS.items():
            render("baseline", name, flags)
            print(f"  rendered {name}")

        for rel, b in backups.items():
            shutil.copyfile(b, REPO / rel)
        print("\n-- FIXED arm (working tree: baseline + the exposure fix) --")
        fsha = build("fixed")
        if fsha == bsha:
            sys.exit(
                "the two builds produced an identical binary; the swap did not "
                "reach the compiler and every comparison below is vacuous"
            )
        for name, flags in ARMS.items():
            render("fixed", name, flags)
            print(f"  rendered {name}")
    finally:
        for rel, b in backups.items():
            shutil.copyfile(b, REPO / rel)
            if (REPO / rel).read_bytes() != live[rel]:
                print(f"!! RESTORE OF {rel} DID NOT MATCH -- backup kept at {b}")
            else:
                print(f"restored {rel} (verified byte-identical)")


def first_strip_offset(p):
    """Where the pixel data starts, read from the TIFF itself.

    Read rather than assumed. A hard-coded boundary is a constant that is right
    until the day the header grows, and then it silently reclassifies pixel
    bytes as header bytes -- which is exactly the direction that turns a real
    regression into a green.
    """
    with tifffile.TiffFile(str(p)) as tf:
        return int(min(tf.pages[0].dataoffsets))


def provenance(buf):
    """The `strehl 0.0.0 (<tree>-dirty)` build stamp the writer embeds.

    This is the source-tree identity, not a statement about the render. It
    moves when a comment moves. It is isolated here so that its bytes can be
    NAMED and subtracted rather than being allowed to pass as "the render
    changed" -- or, worse, waved away as "just metadata" without a count.
    """
    m = re.search(rb"strehl \d+\.\d+\.\d+ \([0-9a-f]+(?:-dirty)?\)", buf)
    return m.group(0).decode() if m else None


def commission():
    """A slope estimator must be shown to move BOTH ways before a null is read.

    0.5x is not decoration. An estimator bounded below at 1.0, or one that has
    quietly become `sxy/sxy`, returns 1.0 for everything and passes a planted
    2.0x on the strength of being broken.
    """
    rng = np.random.default_rng(7)
    x = rng.integers(1, 20000, size=400_000).astype(np.float64)
    for planted in (2.0, 0.5, 1.0):
        y = x * planted
        got = float(x @ y) / float(x @ x)
        ok = abs(got - planted) < 1e-9
        print(
            f"  planted {planted:<6} -> recovered {got:.9f}  "
            f"{'OK' if ok else 'FAIL'}"
        )
        if not ok:
            sys.exit("slope estimator is not commissioned; no verdict below is readable")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("50 -- does the exposure fix move the default render?")
    print("=" * 74)

    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    print(f"HEAD        : {head}")
    print(f"stack       : {STACK} (--limit {LIMIT})")
    print(f"scratch     : {OUT}")

    print("\n-- commissioning the slope estimator --")
    commission()

    analyse_only = "--analyse-only" in sys.argv
    if analyse_only:
        missing = [
            f"{n}.{t}.tif"
            for t in ("baseline", "fixed")
            for n in ARMS
            if not (OUT / f"{n}.{t}.tif").exists()
        ]
        if missing:
            sys.exit(
                "--analyse-only needs both arms already rendered; missing: "
                + ", ".join(missing)
            )
        print("\n-- --analyse-only: reusing the renders already on disk --")

    live = {rel: (REPO / rel).read_bytes() for rel in OWNED}
    base = {rel: head_blob(rel) for rel in OWNED}
    changed = [rel for rel in OWNED if live[rel] != base[rel]]
    print("\n-- commissioning the swap itself --")
    for rel in OWNED:
        same = live[rel] == base[rel]
        print(f"  {rel:<40} {'identical to HEAD' if same else 'DIFFERS from HEAD'}")
    if not changed and not analyse_only:
        sys.exit(
            "the working tree is identical to HEAD for both owned files: the "
            "swap would swap nothing and 'byte-identical' would be vacuous"
        )

    if not analyse_only:
        run_arms(live, base)

    fails = []

    print("\n" + "=" * 74)
    print("REQUIREMENT 4 -- default render must not move")
    print("=" * 74)
    pb = OUT / "B-plain.baseline.tif"
    pf = OUT / "B-plain.fixed.tif"
    hb, hf = sha256(pb), sha256(pf)
    diff, maxd, total, slope, se, n = pixel_verdict(pb, pf)
    print(f"  file sha256 baseline : {hb}")
    print(f"  file sha256 fixed    : {hf}")
    print(f"  whole-file identical : {'YES' if hb == hf else 'NO'}")
    print(f"  samples differing    : {diff:,} of {total:,}   max |delta| {maxd} DN")
    print(f"  delivered slope      : {slope:.7f}")

    # A whole-file hash is NOT the verdict here, and this is the same trap the
    # whole investigation is about: these TIFFs carry their own banner. The
    # `Software` tag embeds the build's source-tree hash, which moves for ANY
    # edit -- a comment, a doc line, a swapped file -- and says nothing about
    # pixels. So the differing bytes are PARTITIONED, and every one of them
    # must be accounted for by name. An unexplained header byte is a failure,
    # not a shrug.
    ba, bf = pb.read_bytes(), pf.read_bytes()
    boundary = first_strip_offset(pb)
    idx = np.nonzero(
        np.frombuffer(ba, dtype=np.uint8) != np.frombuffer(bf, dtype=np.uint8)
    )[0] if len(ba) == len(bf) else None
    if idx is None:
        fails.append("REQ4: the two renders are not even the same length")
    else:
        in_hdr = int((idx < boundary).sum())
        in_pix = int((idx >= boundary).sum())
        print(f"  first strip offset   : {boundary:,}")
        print(f"  differing bytes      : {idx.size} total = {in_hdr} header + {in_pix} pixel")
        prov_b = provenance(ba)
        prov_f = provenance(bf)
        print(f"  provenance baseline  : {prov_b}")
        print(f"  provenance fixed     : {prov_f}")
        explained = 0
        if prov_b is not None and prov_f is not None and prov_b != prov_f:
            explained = sum(1 for x, y in zip(prov_b, prov_f) if x != y)
        print(f"  header bytes explained by the build stamp: {explained} of {in_hdr}")
        if in_pix or diff:
            fails.append(
                f"REQ4: the default --srgb render MOVED ({diff:,} samples, "
                f"{in_pix} pixel bytes)"
            )
        elif explained != in_hdr:
            fails.append(
                f"REQ4: {in_hdr - explained} header byte(s) differ for a reason "
                "nothing has named"
            )
        else:
            print(
                "  VERDICT: UNMOVED -- 0 of 98,898,048 samples differ; the only\n"
                "           difference is the build's own source-tree stamp, which\n"
                "           moves for any edit and reaches no pixel."
            )

    print("\n" + "=" * 74)
    print("DELIVERED GAIN -- the fix must now deliver what was commanded")
    print("=" * 74)
    print(f"  {'pair':<26} {'commanded':>10} {'delivered':>12} {'diff samples':>14}")
    for tag in ("baseline", "fixed"):
        d, mx, tot, sl, se, n = pixel_verdict(
            OUT / f"C-plus3.{tag}.tif", OUT / f"D-minus3.{tag}.tif"
        )
        print(
            f"  D/C {tag:<21} {0.015625:>10.6f} {sl:>12.7f} {d:>14,}"
            f"   (max |d| {mx} DN, +/- {1.96 * se:.2e})"
        )
        if tag == "baseline" and abs(sl - 1.0) > 0.01:
            fails.append("the baseline arm did NOT reproduce the known defect")
        if tag == "fixed" and abs(sl - 0.015625) > 0.015625 * 0.05:
            fails.append(f"the fixed arm delivered {sl:.6f}, not the commanded 0.015625")

    print("\n" + "=" * 74)
    print("--auto-exposure -- declared no-op must be EXACT, not near")
    print("=" * 74)
    for tag in ("baseline", "fixed"):
        d, mx, tot, sl, se, n = pixel_verdict(
            OUT / f"B-plain.{tag}.tif", OUT / f"A-auto.{tag}.tif"
        )
        print(
            f"  A vs B {tag:<10} slope {sl:.7f}  differing {d:,} of {tot:,}"
            f"  max |delta| {mx} DN"
        )
        if tag == "fixed" and d != 0:
            fails.append(f"--auto-exposure still moves {d} samples after supersession")

    print("\n" + "=" * 74)
    if fails:
        for f in fails:
            print(f"FAIL: {f}")
        print(f"VERDICT: {len(fails)} failure(s)")
        return 1
    print("VERDICT: GREEN -- default unmoved, commanded gain delivered, auto exact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
