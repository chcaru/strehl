"""Append section 8 (HEAD test state) to docs/research/BUILD-BLEND.md."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "Test state at HEAD"

NOTE = """
### 8. Test state at HEAD, including a break that is not mine

`cargo test --release -p strehl-core --lib` at a clean checkout of HEAD:
**455 passed, 0 failed.** Run in a detached `git worktree`, not the shared
working tree, because five lanes have uncommitted edits there and a pass in that
tree would not be a statement about HEAD.

`cargo test --release -p strehl-cli --bins` **does not compile at HEAD**:

```
error[E0061]: this method takes 3 arguments but 4 arguments were supplied
    --> crates/strehl-cli/src/merge_cmd.rs:3590:27
    --> crates/strehl-core/src/merge.rs:2063:12
```

Bisected rather than blamed by inspection. Note that plain `cargo build`
succeeds at the broken commit -- the call site is inside a `#[cfg(test)]` path,
so a build-only check reports green and only the test build sees it:

| commit | test build | |
|---|---|---|
| `ab0d71a` | OK | parent of my first commit |
| `0e03579` | OK | |
| `794e605` | **BROKEN** | BUILD-SHARP: wire restore behind STREHL_RESTORE |
| `3db5693` | OK | mine |

An arity mismatch between the veil call site in `merge_cmd.rs` and the method in
`merge.rs`. Both files are outside my lane and none of my four commits touches
either, which is checkable with `git show --name-only`. Flagging rather than
fixing, but flagging loudly: **the CLI test suite cannot run at HEAD**, so
nobody is currently getting a byte-freeze signal from it.

That does not affect the results above. The byte-freezes cannot have moved for
`mean_coarse`: rung 0 is byte-identical to the pre-change render by SHA-256, and
`DEFAULT_MEAN_COARSE` is 0.

One further hazard, recorded because it is invisible in `git status`: the shared
index still holds a snapshot of `scripts/check-defaults.py` that predates
`5ce0fd7`, so a bare `git commit` by any lane would revert my registry entry
while committing their own staged hunk. A path-scoped commit takes the worktree
and is safe. I did not touch the shared index to "fix" this, because another
lane has 31 legitimately staged lines sitting in it.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 8;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
