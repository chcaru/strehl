"""x18 -- the orchestrator's cache-contamination control, run as a measurement.

THE QUESTION (orchestrator broadcast, fact 1446)
------------------------------------------------
"An identical command line produces output hash DB43E708... or ADF81E01...
depending only on whether an unrelated `align --reference 40` ran first."
Cause given: `StackIdentity` covers the frame set but not `reference` and not
`resampler` -- and `resampler` is the field M95 attributes 59% of high-band
loss to.

The prescribed control:
    1. run your arm                                  -> hash A
    2. run an UNRELATED command that changes reference/resampler
    3. re-run your arm, byte-identical command line   -> hash B
    A != B  =>  every number that arm produced tonight is contaminated.

WHAT I FOUND BEFORE RUNNING ANYTHING (read, not measured)
---------------------------------------------------------
The fix already landed. `69f7b4c` at 13:41:53 today, "M97n: key the warp cache
on the solve configuration, not just the path", adds
`solve_config_key(reference, spans, resampler)` (align_cmd.rs:916) which hashes
reference, spans, the resampler's Debug token, and every var in SOLVE_ENV; and
`sidecar_path` (align_cmd.rs:878) mixes that with the canonicalised capture dir.
So on HEAD the two named inputs ARE in the key.

That is a code reading. It is not a measurement, and a fix that is present in
the source is not the same as a fix that works. Hence this file.

MY OWN EXPOSURE
---------------
My renders were written 07:31-07:45 today -- about six hours BEFORE the fix.
Every one of them therefore ran on the unkeyed cache. So "the fix is in HEAD"
does not clear my numbers; the question is whether the code path my renders
actually took ever consulted the broken key at all.

Report line 2041-2044 records that every montage arm set STREHL_WARPMAP and
logged `ON (sidecar-override), reference frame 149, 299 placed / 0 refused`.
The override path loads the named file and hard-validates it with check_stack;
it never calls sidecar_path(). If that is true, my renders were immune even on
the buggy binary. Arm O below tests exactly that, ON THE BUGGY BINARY, which is
the strong form of the claim.

PRE-REGISTERED BARS -- committed before this script was run
-----------------------------------------------------------
Two binaries:
  PRE  = 11e49dd (13:41:44, nine seconds before the fix; verified to contain
         zero `fn solve_config_key` definitions)
  POST = HEAD

Two arms, differing only in whether the sidecar is pinned:
  arm P (plain)    : no STREHL_WARPMAP -- the code path where the defect lives
  arm O (override) : STREHL_WARPMAP pinned -- the path my montage actually took

Each (binary, arm) sequence runs in ONE fresh STREHL_CACHE_DIR shared across
its steps. A fresh cache per step would make the defect unable to manifest by
construction, which would be a rigged null.

  C0  DETERMINISM BASELINE. POST + arm P, run twice with NOTHING between.
      Bar: identical. If these differ, the merge is not run-to-run
      deterministic, no hash comparison here means anything, and I report the
      whole control VOID rather than reporting any of C1-C4.

  C1  POWER CONTROL, MANDATORY (discipline 594 -- my own predecessor's, and it
      binds me). PRE + arm P + intervening `align --reference <k != n/2>`.
      Bar: A != B. This is the instrument saying otherwise. If A == B here I
      have NOT shown the fix works; I have shown my control is blind, and that
      is what I must report.

  C2  THE FIX. POST + arm P, same intervening align.
      Bar: A == B.

  C3  MY MONTAGE'S PATH, ON THE BUGGY BINARY. PRE + arm O.
      Bar: A == B.

  C4  POST + arm O. Bar: A == B.

INTERPRETATION, REGISTERED IN ADVANCE
-------------------------------------
  C0 fails                  -> everything here is VOID. Report that.
  C1 fails (A == B)         -> instrument blind. I report "could not reproduce
                               the defect", NOT "the fix works". No clearance
                               for anyone.
  C1 passes and C3 FAILS    -> my section 22 montage and B23 ringing numbers
                               are CONTAMINATED. Mark them in place with
                               strikethrough, never delete, and say so.
  C1 passes and C3 passes   -> my renders were immune by construction of the
                               override path, on the very binary that carries
                               the defect. Section 22 stands.
  C2 tells the fleet whether M97's landed fix actually holds. It is not about
    my numbers either way.

I do not control what these come back as, and both directions get reported.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- fixed inputs -----------------------------------------------------------
BRACKET = Path(r"D:\personal\macro\coffee-bubbles")  # 19 ARW, read-only
SCRATCH = Path(r"C:\dev\strehl-out\M95-cachectl")
PRE_EXE = SCRATCH / "target-prefix" / "release" / "strehl.exe"
POST_EXE = SCRATCH / "target-post" / "release" / "strehl.exe"
OUT_JSON = Path(__file__).resolve().parents[1] / "out" / "x18_cachectl.json"

PRE_COMMIT = "11e49dd"   # 13:41:44, nine seconds before the fix
POST_COMMIT = "16f2dd2"  # HEAD when this control was run

# Both binaries are built from pinned worktrees under SCRATCH, never from the
# shared target/. That is not fastidiousness -- see the note below.
#
# MEASURED, and it nearly cost me this control: the shared
# `target/release/strehl.exe` carried an mtime of 15:46:49, comfortably after
# the 13:41:53 fix, and I pinned a copy of it as "POST" on that basis. Its own
# `--help` refuted me: no `--exposure`, no `--demosaic`, and the sentence "it
# does not yet align", so it predated M86c, M95 and M100 by hours. A build
# artifact's mtime is evidence of when something touched the file, not of what
# source produced it. The arm died on an unknown-argument error instead of
# silently reporting a stale binary's cache behaviour as HEAD's.
#
# Arguments are the intersection of the two CLIs. `--exposure 1.54`, which my
# montage used, does not exist on the older surface; it is a single multiply in
# linear light applied after the merge and cannot change which sidecar is read,
# so dropping it costs the control nothing.
STACK_ARGS = ["--srgb", "--gate", "4.0"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def die(msg: str) -> None:
    """Tool failure exits 2, never 1.

    Discipline 702: a harness that cannot run must not be confusable with a
    subject that failed its bar. Exit 1 here would read as "contamination
    found", which is a claim about the world; exit 2 reads as "I did not
    measure anything", which is a claim about me.
    """
    print(f"\nTOOL FAILURE: {msg}", file=sys.stderr)
    sys.exit(2)


def run(exe: Path, args: list[str], cache: Path, warpmap: Path | None) -> tuple[int, str]:
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = str(cache)
    env.pop("STREHL_WARPMAP", None)
    env.pop("STREHL_ALIGN", None)
    env.pop("STREHL_FIX_HALO", None)
    if warpmap is not None:
        env["STREHL_WARPMAP"] = str(warpmap)
    r = subprocess.run(
        [str(exe)] + args, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def render(exe: Path, cache: Path, out: Path, warpmap: Path | None) -> tuple[str, str]:
    """One render. Returns (sha256, log). Deletes the tif after hashing."""
    if out.exists():
        out.unlink()
    code, log = run(exe, ["stack", str(BRACKET), *STACK_ARGS, "-o", str(out)], cache, warpmap)
    if code != 0:
        die(f"stack exited {code} (expected 0)\n{log[-4000:]}")
    if not out.exists():
        die(f"no output at {out}\n{log[-4000:]}")
    d = sha256(out)
    out.unlink()
    return d, log


def align_intervene(exe: Path, cache: Path, ref: int) -> str:
    """The UNRELATED command. Must write into the SAME cache dir."""
    code, log = run(exe, ["align", str(BRACKET), "--reference", str(ref)], cache, None)
    if code != 0:
        die(f"align exited {code}\n{log[-4000:]}")
    return log


def fresh(d: Path) -> Path:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def sequence(tag: str, exe: Path, warpmap: Path | None, intervene_ref: int | None) -> dict:
    """Run the prescribed control once. One cache dir across all steps."""
    cache = fresh(SCRATCH / f"cache-{tag}")
    out = SCRATCH / f"{tag}.tif"
    a, log_a = render(exe, cache, out, warpmap)
    mid = ""
    if intervene_ref is not None:
        mid = align_intervene(exe, cache, intervene_ref)
    b, _ = render(exe, cache, out, warpmap)
    token = ""
    for line in log_a.splitlines():
        if "alignment" in line.lower() or "sidecar-override" in line:
            token = line.strip()
            break
    shutil.rmtree(cache, ignore_errors=True)
    return {
        "tag": tag,
        "A": a,
        "B": b,
        "identical": a == b,
        "intervened_reference": intervene_ref,
        "alignment_line": token,
        "align_log_head": "\n".join(mid.splitlines()[:6]),
    }


def main() -> int:
    n = len(sorted(BRACKET.glob("*.ARW")))
    merge_ref = n // 2
    intervene_ref = 0 if merge_ref != 0 else 1
    print(f"bracket {BRACKET.name}: {n} frames, merge reference = {merge_ref}")
    print(f"intervening align --reference {intervene_ref} (deliberately != {merge_ref})")

    for exe in (PRE_EXE, POST_EXE):
        if not exe.exists():
            die(f"missing binary {exe}")
    print(f"PRE  {PRE_EXE}  sha={sha256(PRE_EXE)[:16]}")
    print(f"POST {POST_EXE} sha={sha256(POST_EXE)[:16]}")

    res: dict[str, dict] = {}

    print("\n--- C0 determinism baseline: POST, plain, NOTHING between ---")
    res["C0"] = sequence("c0-post-plain-nointervene", POST_EXE, None, None)
    print(f"  A={res['C0']['A'][:16]}  B={res['C0']['B'][:16]}  identical={res['C0']['identical']}")
    if not res["C0"]["identical"]:
        print("\nC0 FAILED -- the merge is not run-to-run deterministic.")
        print("ENTIRE CONTROL IS VOID. Reporting that and nothing else.")
        OUT_JSON.write_text(json.dumps({"VOID": True, "C0": res["C0"]}, indent=2), encoding="utf-8")
        return 3

    # Build the pinned sidecar for arm O, using the PRE binary, at the merge
    # reference -- so the override names a file that is valid for this bracket.
    pin_cache = fresh(SCRATCH / "cache-pinbuild")
    print(f"\n--- building pinned sidecar (align --reference {merge_ref}) ---")
    code, log = run(PRE_EXE, ["align", str(BRACKET), "--reference", str(merge_ref)], pin_cache, None)
    if code != 0:
        die(f"pin-build align exited {code}\n{log[-4000:]}")
    cands = sorted(pin_cache.rglob("*.warpmap.txt"))
    if len(cands) != 1:
        die(f"expected exactly 1 sidecar, found {len(cands)}: {cands}")
    pinned = SCRATCH / "pinned.warpmap.txt"
    shutil.copy2(cands[0], pinned)
    shutil.rmtree(pin_cache, ignore_errors=True)
    print(f"  pinned sidecar: {pinned.name}, {pinned.stat().st_size} bytes")

    print("\n--- C1 POWER CONTROL: PRE, plain, intervening align ---")
    res["C1"] = sequence("c1-pre-plain", PRE_EXE, None, intervene_ref)
    print(f"  A={res['C1']['A'][:16]}  B={res['C1']['B'][:16]}  identical={res['C1']['identical']}")

    print("\n--- C2 THE FIX: POST, plain, intervening align ---")
    res["C2"] = sequence("c2-post-plain", POST_EXE, None, intervene_ref)
    print(f"  A={res['C2']['A'][:16]}  B={res['C2']['B'][:16]}  identical={res['C2']['identical']}")

    print("\n--- C3 MY MONTAGE PATH ON THE BUGGY BINARY: PRE, override ---")
    res["C3"] = sequence("c3-pre-override", PRE_EXE, pinned, intervene_ref)
    print(f"  A={res['C3']['A'][:16]}  B={res['C3']['B'][:16]}  identical={res['C3']['identical']}")
    print(f"  alignment line: {res['C3']['alignment_line']}")

    print("\n--- C4: POST, override ---")
    res["C4"] = sequence("c4-post-override", POST_EXE, pinned, intervene_ref)
    print(f"  A={res['C4']['A'][:16]}  B={res['C4']['B'][:16]}  identical={res['C4']['identical']}")

    # --- score against the PRE-REGISTERED bars -----------------------------
    verdicts = {
        "C0": (res["C0"]["identical"] is True, "identical (determinism)"),
        "C1": (res["C1"]["identical"] is False, "A != B (power control)"),
        "C2": (res["C2"]["identical"] is True, "identical (fix holds)"),
        "C3": (res["C3"]["identical"] is True, "identical (override immune)"),
        "C4": (res["C4"]["identical"] is True, "identical"),
    }
    print("\n" + "=" * 68)
    print("SCORED AGAINST BARS REGISTERED BEFORE THIS RAN")
    print("=" * 68)
    for k, (ok, bar) in verdicts.items():
        print(f"  {k}: {'PASS' if ok else 'FAIL'}   bar: {bar}")

    blind = not verdicts["C1"][0]
    print()
    if blind:
        print("C1 FAILED. The control never reproduced the defect, so it is BLIND.")
        print("I therefore do NOT conclude the fix works and do NOT clear my own")
        print("renders on the strength of C3. Reported as an untested null.")
    else:
        print("C1 passed: the instrument demonstrably says otherwise.")
        if verdicts["C3"][0]:
            print("C3 passed on the BUGGY binary -> the STREHL_WARPMAP override path")
            print("never consults the broken key. My section 22 renders are immune")
            print("by construction, not by luck. Section 22 stands.")
        else:
            print("C3 FAILED -> my section 22 montage and B23 ringing ARE CONTAMINATED.")
            print("Mark them in place with strikethrough. Do not delete.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "bracket": BRACKET.name,
                "frames": n,
                "merge_reference": merge_ref,
                "intervened_reference": intervene_ref,
                "pre_commit": PRE_COMMIT,
                "post_commit": POST_COMMIT,
                # Recorded separately and deliberately: the repo HEAD at the
                # moment this file is written is NOT the provenance of either
                # binary. Other agents commit continuously, so HEAD moves under
                # a running measurement. The binaries are pinned by worktree
                # commit above and by sha256 below; those are the identities
                # that mean anything.
                "repo_head_at_write_time": subprocess.run(
                    ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                    cwd=str(Path(__file__).resolve().parents[3]),
                ).stdout.strip(),
                "pre_exe_sha256": sha256(PRE_EXE),
                "post_exe_sha256": sha256(POST_EXE),
                "results": res,
                "verdicts": {k: v[0] for k, v in verdicts.items()},
                "blind": blind,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {OUT_JSON}")
    # exit 1 = subject failure (contamination found), 0 = clean, 3 = void
    if blind or not verdicts["C3"][0]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
