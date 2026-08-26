"""Two trees from the SAME commit differing in ONE line, so the clamp is the only
variable. Rendering HEAD against the older pinned binary would confound the clamp
with every other change on the lane since `tree-lin-0d9fd28`.

Both trees are `git archive` exports into scratch. The shared `crates/` is never
touched -- ORCH does not own it and six implementers are editing it live.

The mutation is anchored on a unique full line and HARD-ERRORS if it does not
land. A control that silently fails to apply is indistinguishable from a fix that
works, and this project has already been bitten by exactly that.
"""
import subprocess, sys, pathlib, shutil, hashlib

REPO = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
# cargo is not on PATH for a non-shell subprocess; rustup's default location is.
CARGO = pathlib.Path.home() / ".cargo" / "bin" / "cargo.exe"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\ORCH-CLAMP\interv")
ANCHOR = "            hull: Hull::InputRange,\n"
REPLACE = "            hull: Hull::Unclamped,\n"
TARGET = "crates/strehl-core/src/pyramid.rs"


def sh(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, shell=False)
    if check and r.returncode != 0:
        print(f"FAILED rc={r.returncode}: {' '.join(map(str,args))}")
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(1)
    return r


def export(commit, dest):
    if dest.exists():
        print(f"  {dest.name}: already present, reusing")
        return
    dest.mkdir(parents=True, exist_ok=True)
    tar = dest.parent / f"{dest.name}.tar"
    with open(tar, "wb") as fh:
        r = subprocess.run(["git", "archive", commit], cwd=REPO, stdout=fh)
    if r.returncode != 0:
        sys.exit(f"git archive {commit} failed")
    sh(["tar", "-xf", str(tar), "-C", str(dest)])
    tar.unlink()
    print(f"  {dest.name}: exported {commit}")


def mutate(tree):
    """Apply the negative control. Hard-error unless the tree ends up mutated.

    Idempotent: a re-run finds the anchor already gone and the replacement
    already present, which is success, not failure. The first version treated
    that as MUTATION TARGET NOT FOUND -- correct to refuse a silent no-op, wrong
    about which state it was in.
    """
    p = tree / TARGET
    src = p.read_text(encoding="utf-8")
    n_anchor, n_repl = src.count(ANCHOR), src.count(REPLACE)
    if n_anchor == 0 and n_repl == 1:
        print(f"  {p.relative_to(tree)}: already mutated (idempotent re-run)")
        return
    if n_anchor != 1:
        sys.exit(f"MUTATION TARGET NOT FOUND: {n_anchor} occurrences of anchor and "
                 f"{n_repl} of replacement in {p} (need 1 and 0, or 0 and 1)")
    out = src.replace(ANCHOR, REPLACE, 1)
    if out == src:
        sys.exit("MUTATION DID NOT CHANGE THE FILE")
    p.write_text(out, encoding="utf-8", newline="")
    # Read it back off disk. An in-memory success is not a written file.
    back = p.read_text(encoding="utf-8")
    if REPLACE not in back:
        sys.exit("MUTATION NOT PRESENT ON DISK AFTER WRITE")
    if ANCHOR in back:
        sys.exit("MUTATION LEFT THE ORIGINAL LINE IN PLACE")
    print(f"  mutated {p.relative_to(tree)}: Hull::InputRange -> Hull::Unclamped")


def build(tree, label):
    exe = tree / "target" / "release" / "examples" / "blend-render.exe"
    if exe.exists():
        print(f"  {label}: binary already built, reusing")
    else:
        print(f"  {label}: building (this takes ~3-4 min)...")
        sh([str(CARGO), "build", "--release", "--example", "blend-render"], cwd=tree)
    if not exe.exists():
        sys.exit(f"{label}: build reported success but {exe} is absent")
    h = hashlib.sha256(exe.read_bytes()).hexdigest()[:16]
    print(f"  {label}: {exe}  sha256={h}")
    return exe, h


if __name__ == "__main__":
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # Pin an explicit SHA, not "HEAD". Six implementers commit continuously; HEAD
    # moved 3dfa435 -> 8679d9e between two runs of this script, which would have
    # silently compared two trees built from different commits.
    PIN = sys.argv[1] if len(sys.argv) > 1 else "3dfa435"
    full = sh(["git", "rev-parse", PIN], cwd=REPO).stdout.strip()
    subj = sh(["git", "--no-pager", "log", "-1", "--format=%s", full], cwd=REPO).stdout.strip()
    print(f"commit under test: {PIN} ({full[:12]})\n  {subj}")

    clamped_tree = SCRATCH / "clamped"
    unclamped_tree = SCRATCH / "unclamped"
    export(PIN, clamped_tree)
    export(PIN, unclamped_tree)
    mutate(unclamped_tree)

    # The clamped tree must NOT carry the mutation. Exporting twice from one
    # commit and mutating one is only a controlled comparison if the other is
    # actually pristine.
    ctrl = (clamped_tree / TARGET).read_text(encoding="utf-8")
    if REPLACE in ctrl or ctrl.count(ANCHOR) != 1:
        sys.exit("CONTROL TREE IS CONTAMINATED: clamped/ does not hold Hull::InputRange exactly once")
    print("  clamped tree verified pristine (Hull::InputRange present, mutation absent)")

    a_exe, a_h = build(clamped_tree, "CLAMPED  (as committed)")
    b_exe, b_h = build(unclamped_tree, "UNCLAMPED (negative control)")

    if a_h == b_h:
        sys.exit("THE TWO BINARIES ARE IDENTICAL -- the mutation did not reach the build. "
                 "A one-line control that compiles to the same bytes is testing nothing.")
    print(f"\nbinaries differ ({a_h} vs {b_h}) -- the control reached the build")
    print(f"CLAMPED_EXE={a_exe}")
    print(f"UNCLAMPED_EXE={b_exe}")
