#!/usr/bin/env python3
"""print_ready.py -- a print-readiness gate for strehl master TIFFs.

WHAT THIS IS
    A checker, not a fixer. It answers "would a print lab accept this file?"
    and nothing else. It does not modify masters. BUILD-RENDER owns image_out.rs.

DISCIPLINE (AGENTS.md)
    * Every file x check lands in exactly one of PASS / FAIL / NOT-CHECKED.
      The three counts are asserted to sum to n_files * n_checks, so a check
      that was skipped can never be read as a check that passed.
    * The tool COMMISSIONS ITSELF before it will report on real files. If the
      clean anchor does not pass every check, or if a planted defect is caught
      by a check other than its own, the tool REFUSES to print results.
    * Reading is via tifffile only. PIL silently truncates 16-bit to 8-bit.

ON THE DISTINCT-VALUE CHECK -- why it is a lattice test, not a count
    The obvious way to catch an 8-bit-laundered master is len(np.unique(arr)).
    That count has an innocent explanation: a genuinely simple image (flat
    field, synthetic chart, mostly-black frame) also has few distinct values.
    Gating on the count would FAIL such a file for being simple.

    The lattice stride has no such explanation. Laundered data lies on a
    regular grid -- every value a multiple of 256 (or 257) above the floor --
    so gcd(values - min) >= 2. Real sensor data has gcd 1 no matter how few
    values it holds. Control `c_simple` below is a 16-bit image with only ~40
    distinct values at arbitrary positions: a count gate fails it, the stride
    gate passes it. That control is the reason this check is believable.

    The count is still REPORTED, because it is informative. It is not gated.

    (Note also that the stride test is only valid on the array AS READ FROM
    DISK. Any averaging -- a box mean, a high-pass -- regenerates values off
    the lattice and destroys the evidence while preserving the harm. Never run
    this check on a derived quantity.)

USAGE
    python print_ready.py --commission            # commissioning table only
    python print_ready.py <dir>                   # commission, then scan <dir>
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

import numpy as np
import tifffile

# --------------------------------------------------------------------------
# POLICY THRESHOLDS
#
# These are POLICY, not measurements. They encode "what a print master should
# be", not "what this instrument can detect". They were chosen, not swept, and
# AGENTS.md Sec.77 (a threshold read off the first failing grid point flatters
# the instrument) does not apply to them for that reason -- but it would apply
# the moment anyone quoted one as a detection limit. Do not.
# --------------------------------------------------------------------------
MIN_RESOLUTION = 72.0      # dpi/dpcm below this is a placeholder, not a size
MAX_RESOLUTION = 6000.0    # above this is a unit error
MAX_CLIP_FRAC = 0.005      # 0.5% of samples at pure black or pure white

# Values that are PRESENT but say nothing. Commissioning caught check_metadata
# passing a file whose ImageDescription was tifffile's own '{"shape": [...]}'
# stub -- the same error as reporting HAS DPI: True for (1,1)/NONE. Presence is
# not meaning. LIMIT: only KNOWN placeholders are caught here; an arbitrary
# uninformative string still passes, and this check does not claim otherwise.
PLACEHOLDER_SOFTWARE = {"tifffile.py", "unknown", "n/a"}

PASS, FAIL, NC = "PASS", "FAIL", "NOT-CHECKED"

CHECKS = ["icc", "resolution", "format", "pixels", "levels", "metadata"]

# For each check: the innocent explanation for a FAIL, and the control or
# plant that distinguishes it. Printed by the tool so the reasoning cannot
# drift away from the code that implements it.
RATIONALE = {
    "icc": (
        "innocent: the profile IS present but this reader looks in the wrong "
        "place, so every file fails alike",
        "distinguished by: anchor `clean` carries a real ICC blob and PASSES, "
        "proving the reader finds profiles that exist; and `p_icc_corrupt` "
        "carries a NON-EMPTY blob that FAILS, proving the check validates the "
        "header rather than merely testing that bytes are present",
    ),
    "resolution": (
        "innocent: resolution is stored as a RATIONAL and a reader that "
        "inverts num/den turns a correct 300 dpi into 0.0033",
        "distinguished by: anchor `clean` is written at 300 dpi / INCH and "
        "PASSES, so a FAIL cannot be blamed on rational parsing",
    ),
    "format": (
        "innocent: a 32-bit float master is not 16-bit UINT but is arguably "
        "better, not worse -- this check encodes a policy about what a print "
        "master is, and reports the actual tuple so a reader can judge",
        "distinguished by: only `p_8bit` fails it; the actual BitsPerSample "
        "and SampleFormat are printed in the detail column",
    ),
    "pixels": (
        "innocent: a genuinely simple image (flat field, synthetic chart) has "
        "few distinct values without being laundered",
        "distinguished by: control `c_simple` has ~40 distinct values at "
        "arbitrary positions and PASSES, because the gate is the lattice "
        "stride, not the count",
    ),
    "levels": (
        "innocent: the SUBJECT legitimately contains blown speculars or a "
        "black background, so some clipping is real content, not a defect",
        "distinguished by: only partly. The shoulder fractions are reported "
        "beside the exact-0/exact-max fractions so a reader can see whether "
        "clipped black has a noise shoulder (real dark subject) or none "
        "(clamped). The gate itself is a POLICY cap and is not claimed to "
        "separate the two.",
    ),
    "metadata": (
        "innocent: the tags are present but this reader exposes them under "
        "different names",
        "distinguished by: anchor `clean` carries both and PASSES. TWO plants, "
        "because presence is not meaning: `p_meta_absent` (tag genuinely "
        "missing) and `p_meta_stub` (tags PRESENT, holding the writer's own "
        "placeholders). The stub plant exists because commissioning caught "
        "this check passing a file described as '{\"shape\": [...]}'. LIMIT: "
        "only KNOWN placeholders are caught; an arbitrary uninformative "
        "string still passes.",
    ),
}


class _FakeTag:
    """Minimal stand-in for a tifffile tag, for unit-level commissioning."""

    def __init__(self, value):
        self.value = value


# --------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------
def hist_u16(arr: np.ndarray) -> np.ndarray:
    """Full 65536-bin histogram, accumulated in chunks to bound memory.

    A SHIP-V2 master is 7032x4688x3 = 98.9M samples; bincount on the whole
    array would allocate an intp temporary of ~800 MB.
    """
    h = np.zeros(65536, dtype=np.int64)
    flat = arr.ravel()
    step = 8_000_000
    for i in range(0, flat.size, step):
        h += np.bincount(flat[i : i + step], minlength=65536)
    return h


def pct_from_hist(hist: np.ndarray, q: float) -> int:
    """Exact percentile for integer data, from the cumulative histogram."""
    cum = np.cumsum(hist)
    n = int(cum[-1])
    if n == 0:
        return -1
    target = q / 100.0 * n
    return int(min(np.searchsorted(cum, target, side="left"), hist.size - 1))


def lattice_stride(values: np.ndarray) -> int:
    """gcd of the gaps between present values.

    1 for real data; 256 or 257 for an 8-bit-laundered master. Returns 0 when
    fewer than two distinct values exist (degenerate, handled by the caller).
    """
    if values.size < 2:
        return 0
    return int(np.gcd.reduce((values - values[0]).astype(np.int64)))


# --------------------------------------------------------------------------
# individual checks -- each returns (status, detail)
# --------------------------------------------------------------------------
def check_icc(tags) -> tuple[str, str]:
    tag = tags.get("InterColorProfile") or tags.get(34675)
    if tag is None:
        return FAIL, "no InterColorProfile tag (34675)"
    blob = tag.value
    if blob is None or len(blob) == 0:
        return FAIL, "InterColorProfile present but empty"
    blob = bytes(blob)
    n = len(blob)
    if n < 132:
        return FAIL, f"profile truncated: {n} bytes, header alone is 128"
    if blob[36:40] != b"acsp":
        return FAIL, f"bad signature at offset 36: {blob[36:40]!r} != b'acsp'"
    declared = int.from_bytes(blob[0:4], "big")
    if declared != n:
        return FAIL, f"size field {declared} != actual blob length {n}"
    devclass = blob[12:16]
    space = blob[16:20]
    pcs = blob[20:24]
    if devclass not in (b"mntr", b"scnr", b"prtr", b"spac", b"link", b"abst", b"nmcl"):
        return FAIL, f"unknown device class {devclass!r}"
    if space not in (b"RGB ", b"GRAY", b"CMYK"):
        return FAIL, f"unexpected data colour space {space!r}"
    if pcs not in (b"XYZ ", b"Lab "):
        return FAIL, f"unexpected PCS {pcs!r}"
    return PASS, (
        f"{n} B, class={devclass.decode()}, space={space.decode().strip()}, "
        f"pcs={pcs.decode().strip()}"
    )


def check_resolution(tags) -> tuple[str, str]:
    unit_tag = tags.get("ResolutionUnit")
    xr = tags.get("XResolution")
    yr = tags.get("YResolution")
    if unit_tag is None or xr is None or yr is None:
        missing = [
            n
            for n, t in (("ResolutionUnit", unit_tag), ("XResolution", xr), ("YResolution", yr))
            if t is None
        ]
        return FAIL, "missing tag(s): " + ", ".join(missing)
    unit = int(unit_tag.value)
    unit_name = {1: "NONE", 2: "INCH", 3: "CENTIMETER"}.get(unit, f"?{unit}")

    def as_float(v):
        if isinstance(v, tuple) and len(v) == 2:
            return float(v[0]) / float(v[1]) if v[1] else float("nan")
        return float(v)

    x, y = as_float(xr.value), as_float(yr.value)
    if unit == 1:
        return FAIL, f"ResolutionUnit=NONE, res=({x:g},{y:g}) -- a ratio, not a print size"
    if unit not in (2, 3):
        return FAIL, f"ResolutionUnit={unit_name}, res=({x:g},{y:g})"
    if not (MIN_RESOLUTION <= x <= MAX_RESOLUTION and MIN_RESOLUTION <= y <= MAX_RESOLUTION):
        return FAIL, (
            f"unit={unit_name} but res=({x:g},{y:g}) outside "
            f"[{MIN_RESOLUTION:g},{MAX_RESOLUTION:g}]"
        )
    return PASS, f"{x:g}x{y:g} per {unit_name.lower()}"


def check_format(tags) -> tuple[str, str]:
    bps = tags.get("BitsPerSample")
    spp = tags.get("SamplesPerPixel")
    sf = tags.get("SampleFormat")
    photo = tags.get("PhotometricInterpretation")
    if bps is None or spp is None or photo is None:
        return FAIL, "missing BitsPerSample / SamplesPerPixel / Photometric"
    bps_v = bps.value if isinstance(bps.value, tuple) else (bps.value,)
    spp_v = int(spp.value)
    sf_v = (
        (sf.value if isinstance(sf.value, tuple) else (sf.value,)) if sf is not None else None
    )
    photo_v = int(photo.value)
    parts = [f"bps={tuple(int(b) for b in bps_v)}", f"spp={spp_v}", f"photo={photo_v}"]
    parts.append(f"sf={tuple(int(s) for s in sf_v)}" if sf_v is not None else "sf=absent")
    detail = " ".join(parts)
    bad = []
    if tuple(int(b) for b in bps_v) != (16, 16, 16):
        bad.append("not 16/16/16")
    if spp_v != 3:
        bad.append("not 3 samples")
    if photo_v != 2:
        bad.append("not RGB")
    # SampleFormat absent means UINT by TIFF default -- that is legal.
    if sf_v is not None and any(int(s) != 1 for s in sf_v):
        bad.append("not UINT")
    if bad:
        return FAIL, detail + "  <- " + "; ".join(bad)
    return PASS, detail


def check_pixels(arr, hist) -> tuple[str, str]:
    if arr.dtype != np.uint16:
        return NC, f"dtype={arr.dtype}, lattice gate is scoped to uint16 (see `format`)"
    if not np.isfinite(arr).all():
        return FAIL, "array contains NaN or Inf"
    present = np.nonzero(hist)[0]
    ndist = int(present.size)
    if ndist == 0:
        return FAIL, "empty array"
    amax = int(present[-1])
    if amax == 0:
        return FAIL, "max == 0, image is entirely black"
    if ndist == 1:
        return FAIL, f"degenerate: a single distinct value ({amax})"
    stride = lattice_stride(present)
    if stride >= 2:
        return FAIL, (
            f"values lie on a lattice of stride {stride} "
            f"({ndist} distinct) -- 8-bit data in a 16-bit container"
        )
    return PASS, f"{ndist} distinct, stride 1, max {amax}"


def check_levels(arr, hist) -> tuple[str, str]:
    if arr.dtype != np.uint16:
        return NC, f"dtype={arr.dtype}, black/white points are scoped to uint16"
    n = int(hist.sum())
    if n == 0:
        return NC, "empty array"
    f_zero = hist[0] / n
    f_max = hist[65535] / n
    # Shoulders: if a dark subject is real, values scatter just above 0. If it
    # was clamped, the shoulder is empty and everything sits exactly at 0.
    sh_lo = hist[1:256].sum() / n
    sh_hi = hist[65280:65535].sum() / n
    p_lo = pct_from_hist(hist, 0.01)
    p_hi = pct_from_hist(hist, 99.99)
    detail = (
        f"p0.01={p_lo} p99.99={p_hi} zero={f_zero * 100:.4f}% "
        f"max={f_max * 100:.4f}% (shoulders lo={sh_lo * 100:.4f}% hi={sh_hi * 100:.4f}%)"
    )
    bad = []
    if f_zero > MAX_CLIP_FRAC:
        bad.append(f"black clip {f_zero * 100:.3f}% > {MAX_CLIP_FRAC * 100:g}%")
    if f_max > MAX_CLIP_FRAC:
        bad.append(f"white clip {f_max * 100:.3f}% > {MAX_CLIP_FRAC * 100:g}%")
    if bad:
        return FAIL, detail + "  <- " + "; ".join(bad)
    return PASS, detail


def _is_shape_stub(v: str) -> bool:
    s = v.strip()
    return s.startswith('{"shape"') or s.startswith("{'shape'")


def check_metadata(tags) -> tuple[str, str]:
    problems: list[str] = []
    got: list[str] = []

    t = tags.get("Software")
    sw = t.value if t is not None else None
    if sw is None or not str(sw).strip():
        problems.append("Software absent/empty")
    elif str(sw).strip() in PLACEHOLDER_SOFTWARE:
        problems.append(f"Software is a writer placeholder ({str(sw)!r})")
    else:
        got.append(f"Software={str(sw)[:28]!r}")

    t = tags.get("ImageDescription")
    de = t.value if t is not None else None
    if de is None or not str(de).strip():
        problems.append("ImageDescription absent/empty")
    elif _is_shape_stub(str(de)):
        problems.append(f"ImageDescription is a writer shape stub ({str(de)[:30]!r})")
    else:
        got.append(f"ImageDescription={len(str(de))}ch")

    if problems:
        d = "; ".join(problems)
        if got:
            d += "  present: " + ", ".join(got)
        return FAIL, d
    return PASS, ", ".join(got)


# --------------------------------------------------------------------------
# per-file driver
# --------------------------------------------------------------------------
def inspect(path: str) -> dict[str, tuple[str, str]]:
    """Return {check: (status, detail)} for one file, always all CHECKS."""
    out: dict[str, tuple[str, str]] = {}
    try:
        with tifffile.TiffFile(path) as tf:
            page = tf.pages[0]
            tags = page.tags
            out["icc"] = check_icc(tags)
            out["resolution"] = check_resolution(tags)
            out["format"] = check_format(tags)
            out["metadata"] = check_metadata(tags)
            try:
                arr = page.asarray()
            except Exception as exc:
                for k in ("pixels", "levels"):
                    out[k] = (NC, f"array unreadable: {type(exc).__name__}: {exc}")
                return out
            hist = hist_u16(arr) if arr.dtype == np.uint16 else np.zeros(65536, np.int64)
            out["pixels"] = check_pixels(arr, hist)
            out["levels"] = check_levels(arr, hist)
            del arr
    except Exception as exc:
        for k in CHECKS:
            out.setdefault(k, (NC, f"open failed: {type(exc).__name__}: {exc}"))
    for k in CHECKS:
        out.setdefault(k, (NC, "check did not run"))
    return out


def verdict(res: dict[str, tuple[str, str]]) -> str:
    st = [res[c][0] for c in CHECKS]
    if FAIL in st:
        return FAIL
    if NC in st:
        return NC
    return PASS


# --------------------------------------------------------------------------
# commissioning
# --------------------------------------------------------------------------
def minimal_icc(corrupt: bool = False) -> bytes:
    """A structurally valid 132-byte ICC (header + empty tag table).

    Enough to exercise every field this checker reads. It is NOT a usable
    colour profile and this tool does not claim to validate profile SEMANTICS
    -- only the header that a lab's software parses first.
    """
    body = bytearray(132)
    body[4:8] = b"none"
    body[8:12] = (0x02100000).to_bytes(4, "big")
    body[12:16] = b"mntr"
    body[16:20] = b"RGB "
    body[20:24] = b"XYZ "
    body[36:40] = b"scsp" if corrupt else b"acsp"  # <- the planted defect
    body[64:68] = (0).to_bytes(4, "big")
    body[0:4] = len(body).to_bytes(4, "big")
    return bytes(body)


def _write(path, data, *, icc=None, res=(300, 300), unit="INCH", meta="full"):
    extra = []
    if icc is not None:
        extra.append((34675, 7, len(icc), icc, True))
    kw = {}
    if meta == "full":
        kw["description"] = "commissioning sample for print_ready.py"
        kw["software"] = "print_ready-commission"
    elif meta == "absent":
        # metadata=None suppresses ImageDescription. software=None does NOT
        # suppress Software -- tifffile writes 'tifffile.py' regardless, which
        # is why the Software-absent branch is commissioned at unit level.
        kw["metadata"] = None
        kw["software"] = None
    elif meta == "stub":
        pass  # let tifffile install its own placeholders
    else:
        raise ValueError(f"unknown meta mode {meta!r}")
    if res is not None:
        kw["resolution"] = res
        kw["resolutionunit"] = unit
    tifffile.imwrite(path, data, photometric="rgb", extratags=extra, **kw)


def build_plants(scratch: str, rng) -> list[tuple[str, str, str]]:
    """Write the anchor, the plants and the false-positive control.

    Returns [(name, path, expected_failing_check_or_empty)].
    """
    os.makedirs(scratch, exist_ok=True)
    h, w = 192, 256
    base = rng.integers(1000, 60000, size=(h, w, 3), dtype=np.uint16)
    icc = minimal_icc()

    specs: list[tuple[str, str, str]] = []

    def add(name, expect, data, **kw):
        p = os.path.join(scratch, name + ".tiff")
        _write(p, data, **kw)
        specs.append((name, p, expect))

    # anchor -- must pass every check. If it does not, everything below is
    # uninterpretable and the tool refuses to run.
    add("clean", "", base, icc=icc)

    add("p_icc_absent", "icc", base, icc=None)
    add("p_icc_corrupt", "icc", base, icc=minimal_icc(corrupt=True))
    add("p_res_none", "resolution", base, icc=icc, res=(1, 1), unit="NONE")
    add("p_8bit", "format", (base >> 8).astype(np.uint8), icc=icc)

    laundered = ((base >> 8) << 8).astype(np.uint16)
    add("p_laundered", "pixels", laundered, icc=icc)

    clipped = base.copy()
    m = rng.random(size=(h, w)) < 0.30
    clipped[m] = 65535
    add("p_clip", "levels", clipped, icc=icc)

    add("p_meta_absent", "metadata", base, icc=icc, meta="absent")
    add("p_meta_stub", "metadata", base, icc=icc, meta="stub")

    # false-positive control: genuinely simple, genuinely 16-bit. A check that
    # gated on the DISTINCT COUNT would fail this file. The lattice gate must
    # pass it. Assert the construction really is off-lattice, so a control that
    # failed to apply raises here rather than passing quietly.
    vals = rng.choice(np.arange(1000, 60000, dtype=np.uint16), size=40, replace=False)
    if lattice_stride(np.sort(vals)) != 1:
        raise RuntimeError("c_simple construction degenerate: values fell on a lattice")
    simple = vals[rng.integers(0, 40, size=(h, w, 3))].astype(np.uint16)
    add("c_simple", "", simple, icc=icc)

    return specs


def run_unit_commission() -> bool:
    """Exercise check branches that the writer cannot produce end-to-end.

    tifffile.imwrite always emits Software='tifffile.py', so no plant can give
    a file with Software genuinely absent. That branch is driven directly here.
    Labelled UNIT so it is never mistaken for an end-to-end result.
    """
    print("  UNIT-LEVEL COMMISSIONING (branches unreachable through the writer)")
    real = "sRGB (IEC 61966-2-1): BT.709-6 primaries, D65 white point"
    cases = [
        ("Software absent", {"ImageDescription": _FakeTag(real)}, FAIL),
        (
            "Software placeholder",
            {"Software": _FakeTag("tifffile.py"), "ImageDescription": _FakeTag(real)},
            FAIL,
        ),
        ("ImageDescription absent", {"Software": _FakeTag("strehl 1.2.3")}, FAIL),
        (
            "ImageDescription shape stub",
            {
                "Software": _FakeTag("strehl 1.2.3"),
                "ImageDescription": _FakeTag('{"shape": [192, 256, 3]}'),
            },
            FAIL,
        ),
        # two-sided: the check must also be capable of saying PASS, or a
        # check that failed everything would look fully commissioned.
        (
            "both meaningful",
            {"Software": _FakeTag("strehl 1.2.3"), "ImageDescription": _FakeTag(real)},
            PASS,
        ),
    ]
    ok = True
    for name, tags, expect in cases:
        st, _ = check_metadata(dict(tags))
        good = st == expect
        ok = ok and good
        print(
            "    %-30s -> %-11s expected %-11s %s"
            % (name, st, expect, "ok" if good else "MISMATCH")
        )
    return ok


def run_commission(scratch: str, keep: bool = False) -> bool:
    rng = np.random.default_rng(20260826)
    print("=" * 100)
    print("COMMISSIONING -- the checker must FAIL on damage before it may report on masters")
    print("=" * 100)
    print(f"scratch: {scratch}")
    print()
    try:
        specs = build_plants(scratch, rng)
    except Exception as exc:
        print(f"  PLANT CONSTRUCTION FAILED: {type(exc).__name__}: {exc}")
        return False

    hdr = "  %-15s %-11s " % ("sample", "expect") + " ".join("%-10s" % c[:10] for c in CHECKS)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    ok = True
    notes: list[str] = []
    for name, path, expect in specs:
        res = inspect(path)
        cells = []
        for c in CHECKS:
            s = res[c][0]
            cells.append({PASS: "pass", FAIL: "FAIL", NC: "n/c"}[s])
        print("  %-15s %-11s " % (name, expect or "(all pass)") + " ".join("%-10s" % x for x in cells))

        # orthogonality: exactly the expected check fails, and no other.
        failed = [c for c in CHECKS if res[c][0] == FAIL]
        if expect:
            if failed != [expect]:
                ok = False
                notes.append(
                    f"    {name}: expected exactly ['{expect}'] to FAIL, got {failed} "
                    f"-- a defect is being masked by, or masking, a neighbour"
                )
        else:
            if failed:
                ok = False
                notes.append(f"    {name}: anchor must pass everything, but {failed} FAILED")
            nc = [c for c in CHECKS if res[c][0] == NC]
            if nc:
                ok = False
                notes.append(f"    {name}: anchor must be fully CHECKED, but {nc} were NOT-CHECKED")

    print()
    for name, path, expect in specs:
        res = inspect(path)
        for c in CHECKS:
            if res[c][0] != PASS:
                print(f"    {name:<15} {c:<11} {res[c][0]:<11} {res[c][1]}")

    if notes:
        print("\n  ORTHOGONALITY VIOLATIONS")
        for n in notes:
            print(n)

    print()
    print("  WHAT EACH CHECK'S FAIL COULD INNOCENTLY MEAN, AND WHAT RULES IT OUT")
    for c in CHECKS:
        inn, dist = RATIONALE[c]
        print(f"    {c}")
        print(f"        {inn}")
        print(f"        {dist}")

    if not keep:
        shutil.rmtree(scratch, ignore_errors=True)

    print()
    unit_ok = run_unit_commission()
    ok = ok and unit_ok

    print()
    print(f"  COMMISSIONING: {'PASS' if ok else 'FAIL'}")
    return ok


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------
def run_scan(directory: str) -> int:
    files = sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.splitext(f)[1].lower() == ".tiff"
    )
    print()
    print("=" * 100)
    print(f"SCAN -- {directory}")
    print("=" * 100)
    print(f"  {len(files)} files with extension exactly '.tiff'")
    print()

    # Column width from the data, not a guess. A fixed %-34s silently truncated
    # six of the 26 names on the first real run -- a formatting choice that
    # removes information is the same defect class as everything else here.
    names = [os.path.basename(p) for p in files]
    w = max([len("file")] + [len(n) for n in names])

    hdr = f"  %-{w}s %-8s " % ("file", "verdict") + " ".join("%-10s" % c[:10] for c in CHECKS)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    tally = {PASS: 0, FAIL: 0, NC: 0}
    per_check = {c: {PASS: 0, FAIL: 0, NC: 0} for c in CHECKS}
    details: dict[str, list[str]] = {}
    verdicts = {PASS: 0, FAIL: 0, NC: 0}

    for p in files:
        res = inspect(p)
        v = verdict(res)
        verdicts[v] += 1
        cells = []
        for c in CHECKS:
            s = res[c][0]
            tally[s] += 1
            per_check[c][s] += 1
            cells.append({PASS: "pass", FAIL: "FAIL", NC: "n/c"}[s])
        print(
            f"  %-{w}s %-8s " % (os.path.basename(p), {PASS: "PASS", FAIL: "FAIL", NC: "N/C"}[v])
            + " ".join("%-10s" % x for x in cells)
        )
        for c in CHECKS:
            if res[c][0] != PASS:
                details.setdefault(c, []).append(res[c][1])

    total = len(files) * len(CHECKS)
    got = tally[PASS] + tally[FAIL] + tally[NC]
    print()
    print("  PARTITION (every file x check lands in exactly one bucket)")
    print(f"    files {len(files)}  x  checks {len(CHECKS)}  =  {total} cells")
    print(f"    PASS {tally[PASS]}   FAIL {tally[FAIL]}   NOT-CHECKED {tally[NC]}   sum {got}")
    assert got == total, f"PARTITION BROKEN: {got} != {total}"
    print("    partition verified: sum == total")

    print()
    print("  PER-CHECK")
    for c in CHECKS:
        d = per_check[c]
        print(f"    {c:<12} pass {d[PASS]:>3}   FAIL {d[FAIL]:>3}   n/c {d[NC]:>3}")

    print()
    print("  PER-FILE VERDICT")
    for k, lbl in ((PASS, "PASS"), (FAIL, "FAIL"), (NC, "NOT-CHECKED")):
        print(f"    {lbl:<12} {verdicts[k]:>3}")

    print()
    print("  REPRESENTATIVE NON-PASS DETAIL (distinct messages per check)")
    for c in CHECKS:
        if c in details:
            seen = sorted(set(details[c]))
            print(f"    {c}:")
            for s in seen[:4]:
                n = details[c].count(s)
                print(f"        [{n:>3}x] {s}")
            if len(seen) > 4:
                print(f"        ... {len(seen) - 4} further distinct messages")

    return 1 if verdicts[FAIL] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="print-readiness gate for strehl masters")
    ap.add_argument("directory", nargs="?", help="directory of .tiff masters")
    ap.add_argument("--commission", action="store_true", help="commissioning only")
    ap.add_argument(
        "--scratch",
        default=r"C:\dev\strehl-out\BUILD-HIGHLIGHT\printready-commission",
        help="where commissioning samples are written",
    )
    ap.add_argument("--keep", action="store_true", help="keep commissioning samples")
    a = ap.parse_args()

    ok = run_commission(a.scratch, keep=a.keep)
    if a.commission:
        return 0 if ok else 2
    if not a.directory:
        ap.error("a directory is required unless --commission is given")
    if not ok:
        print()
        print("  REFUSING TO SCAN: commissioning failed, so a clean result would be")
        print("  indistinguishable from a deaf one. Fix the checker first.")
        return 2
    return run_scan(a.directory)


if __name__ == "__main__":
    sys.exit(main())
