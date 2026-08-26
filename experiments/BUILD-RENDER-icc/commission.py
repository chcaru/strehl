"""Commission the ICC unit tests: plants they must catch, a null they must not move.

A test suite that has never failed is not evidence. Each plant below is a defect
a reader would plausibly introduce, and the named test must go RED for it. The
null is a no-op edit that must stay GREEN, which proves the harness is not simply
reporting RED for any edit at all.

Restore is from a $env:TEMP pin, never `git checkout --`. The file's mtime is
bumped after restore because Copy-Item/copy2 preserve it and cargo would then
reuse stale artifacts and report the previous arm's result.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "crates" / "strehl-cli" / "src" / "image_out.rs"
CARGO = Path(os.environ["USERPROFILE"]) / ".cargo" / "bin" / "cargo.exe"
FILTER = "image_out"

# (name, anchor, replacement, tests that MUST fail)
PLANTS = [
    (
        "no-chromatic-adaptation",
        "    let adapt = mat3_mul(mat3_inv(BRADFORD), mat3_mul(scale, BRADFORD));\n"
        "    mat3_mul(adapt, m)\n",
        "    m\n",
        ["the_derived_primaries_match_the_published_srgb_icc_columns",
         "the_primary_columns_sum_to_the_pcs_white"],
    ),
    (
        "transposed-primary-matrix",
        "            m[i][j] = p[i][j] * s[j];\n",
        "            m[i][j] = p[j][i] * s[i];\n",
        ["the_derived_primaries_match_the_published_srgb_icc_columns"],
    ),
    (
        "trc-stored-backwards",
        "fn srgb_eotf(v: f64) -> f64 {\n"
        "    if v <= 0.040_45 {\n"
        "        v / 12.92\n"
        "    } else {\n"
        "        ((v + 0.055) / 1.055).powf(2.4)\n"
        "    }\n"
        "}\n",
        "fn srgb_eotf(v: f64) -> f64 {\n"
        "    if v <= 0.003_130_8 {\n"
        "        12.92 * v\n"
        "    } else {\n"
        "        1.055 * v.powf(1.0 / 2.4) - 0.055\n"
        "    }\n"
        "}\n",
        ["the_transfer_curve_is_stored_in_the_decoding_direction"],
    ),
    (
        "srgb-profile-on-camera-native",
        "        (false, _) => None,\n",
        "        (false, _) => Some(icc_srgb_v2(true)),\n",
        ["only_the_colorimetric_paths_get_a_profile"],
    ),
    (
        "creation-date-from-the-clock",
        "    for v in [2026u16, 1, 1, 0, 0, 0] {\n",
        "    for v in [2026u16, 1, 1, 0, 0, PLANT_NONDET.fetch_add(1, "
        "std::sync::atomic::Ordering::Relaxed) as u16] {\n",
        ["the_profile_is_structurally_well_formed_and_deterministic"],
    ),
    (
        "profile-size-field-not-updated",
        "    out.extend_from_slice(&(total as u32).to_be_bytes()); // profile size\n",
        "    out.extend_from_slice(&(total as u32 + 4).to_be_bytes()); // profile size\n",
        ["the_profile_is_structurally_well_formed_and_deterministic"],
    ),
]

# Support code a plant needs; appended only while that plant is installed.
PLANT_SUPPORT = """
#[allow(dead_code)]
static PLANT_NONDET: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
"""

NULL = (
    "a-comment-only-edit",
    "fn srgb_eotf(v: f64) -> f64 {\n",
    "fn srgb_eotf(v: f64) -> f64 {\n    // commissioning null: no behaviour change\n",
)


def run_tests() -> tuple[bool, str]:
    p = subprocess.run(
        [str(CARGO), "test", "-p", "strehl-cli", "--bins", FILTER],
        cwd=ROOT, capture_output=True, text=True,
    )
    return p.returncode == 0, p.stdout + p.stderr


def failing(out: str) -> set[str]:
    got = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("test image_out::tests::") and line.endswith("FAILED"):
            got.add(line.split("::")[-1].removesuffix(" ... FAILED").strip())
    return got


def apply(text: str, anchor: str, repl: str, label: str) -> str:
    n = text.count(anchor)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND for {label!r}: anchor occurs {n} times, "
            "expected exactly 1. A plant that does not land is indistinguishable "
            "from a plant the tests caught, so this is fatal rather than skipped."
        )
    return text.replace(anchor, repl, 1)


def main() -> int:
    pin = Path(tempfile.gettempdir()) / "image_out.rs.commission-pin"
    shutil.copy2(SRC, pin)
    original = SRC.read_text(encoding="utf-8")
    print(f"pinned {SRC.name} -> {pin}\n")

    caught: list[tuple[str, str]] = []
    missed: list[tuple[str, list[str]]] = []
    null_ok = False
    try:
        ok, out = run_tests()
        if not ok:
            print("BASELINE IS ALREADY RED -- commissioning would be meaningless")
            print(out[-3000:])
            return 2
        print("baseline GREEN\n")

        for name, anchor, repl, must_fail in PLANTS:
            SRC.write_text(apply(original, anchor, repl, name) + PLANT_SUPPORT, encoding="utf-8")
            os.utime(SRC, None)
            ok, out = run_tests()
            got = failing(out)
            compiled = "error: could not compile" not in out
            hit = sorted(set(must_fail) & got)
            if not compiled:
                caught.append((name, "rejected at compile time"))
                print(f"  CAUGHT  {name}: refused to compile")
            elif hit:
                caught.append((name, ", ".join(hit)))
                print(f"  CAUGHT  {name}: {', '.join(hit)}")
            else:
                missed.append((name, sorted(got)))
                print(f"  MISSED  {name}: wanted {must_fail}, got {sorted(got) or 'no failures'}")

        name, anchor, repl = NULL
        SRC.write_text(apply(original, anchor, repl, name), encoding="utf-8")
        os.utime(SRC, None)
        null_ok, _ = run_tests()
        print(f"\n  NULL    {name}: {'GREEN (correct)' if null_ok else 'RED -- INSTRUMENT IS TWITCHY'}")
    finally:
        shutil.copy2(pin, SRC)
        os.utime(SRC, None)
        assert SRC.read_text(encoding="utf-8") == original, "restore did not reproduce the original"
        print(f"\nrestored {SRC.name} from pin, content verified byte-identical")

    total = len(PLANTS)
    assert len(caught) + len(missed) == total, "outcomes do not partition the plants"
    print(f"\nplants: caught {len(caught)} / missed {len(missed)} / total {total}")
    print(f"null held: {null_ok}")
    ok = not missed and null_ok
    print("COMMISSIONED" if ok else "NOT COMMISSIONED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
