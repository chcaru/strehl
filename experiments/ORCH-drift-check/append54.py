"""Append section 54 to ORCH-veiling.md. One-shot; idempotent by anchor check."""
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "research" / "ORCH-veiling.md"

ANCHOR = "## 54. The sharpness module has no callers"

SECTION = """

## 54. The sharpness module has no callers, and the complaint is softness

The project measured that its own alignment gather costs **1.43x in amplitude at
f=0.35**, confirmed that arithmetic against a real fold to **1.8%**, wrote a
noise-aware module to correct it, and **never connected the module to the
product**. The owner's verdict on the shipped gallery is that it looks bad, and
the quality he is describing is softness.

### 54.1 How I know it has no callers

`crates/strehl-core/src/restore.rs` is 33,461 bytes and exports a complete,
self-testing surface: `gather_mtf`, `RestoreConfig::gain(f, signal_power)`,
`gain_2d`, `RestoreReport`, `autocorrelation`, `design_fir`, `restore_plane`,
`selftest`. `strehl-core/src/lib.rs:29` declares `pub mod restore;`, so it
compiles, raises no dead-code warning, and appears alive to anyone reading the
module list.

I checked reachability rather than inferring it, because section 53 had just
cost the project a headline for exactly that mistake:

- `restore|deconv|unsharp|sharpen|mtf` across `merge_cmd.rs` matches only
  `sharpen_per_octave` at L4178 and L4272, plus a comment at L5103.
- Case-insensitive `restore` across all of `crates/strehl-cli/src/` returns
  **four** hits: `image_out.rs:1512`, `image_out.rs:1554`, `merge_cmd/dump.rs:103`,
  `align_cmd.rs:530`. **I read all four. Every one is the English word
  "restores" inside a comment.** There is no `strehl_core::restore` reference
  anywhere in the CLI crate.
- The only real consumer in the repository is
  `crates/strehl-core/examples/restore-plane.rs` -- an **example** binary, on no
  product path.

A count of four looked at first glance like the module was wired. Reading the
four lines is what turned a plausible yes into a certain no. **A grep count is
not a reachability result; the matched lines are.**

### 54.2 This is a third distinct failure mode, not a repeat

The project has now logged three ways for work to fail to reach the product, and
they need different defences:

| section | failure | signature |
| --- | --- | --- |
| 49, 51 | instrument and product on opposite sides of a transformation | measurements that do not predict the render |
| 52 | a stage exists on the path but is skipped by this backend | the tool prints `not applied: ...` |
| **54** | **code compiles, is complete, is never called** | **nothing at all -- it is invisible** |

The third is the worst of the three, because the other two announce themselves.
A byte comparison across a version gap catches the first. The tool's own banner
catches the second. **Nothing catches the third**, which is why it survived a
research programme that has otherwise been unusually careful, and survived at
least two audits aimed near it.

### 54.3 The rule

> **A module that compiles is not a module that runs. For every finding the
> project claims to have applied, name the call site.** Not the module, not the
> function -- the line on the product path that invokes it, established from the
> call graph and confirmed against the shipped artefact.

The corollary is that "is it wired?" must be asked of *findings*, not of code.
Code review looks at what is there. This defect is entirely about what is
*absent*, and absence has no diff to review.

### 54.4 I had looked at the pixels, and still had not looked at the picture

Section 53.1 records that I inspected `bee-3-cpl.tiff` at 1:1 and certified it.
That is true, and it did not help, because I was answering a **resolution**
question -- is this 7032x4688 and three-channel -- and never asked *is this
good*. Tonight I opened the contact sheet and the 1:1 print-QA sheets to judge
them as photographs for the first time. `lavendar-cpl` renders its hairs as
low-microcontrast mush; `flowers-cpl`, `wrapped-text-2` and
`highly-angled-ruler-mm-cpl` are visibly soft **at one-eighth scale**, which is
severe.

This is the same shape as section 53's closing lesson -- a number recorded under
one heading is not consulted when the question arrives under another -- and it
generalises past numbers to images. **Looking at an image to measure it is not
the same act as looking at it to judge it, and the first does not discharge the
second.** An implementer in another lane reported the identical failure twice in
one night, in its own words: *"I did not look at it as a picture."*

### 54.5 What the gallery actually is, settled from the driver

Worth pinning, because it was assumed twice and is load-bearing for how the
owner's complaint should be read. `C:\\dev\\strehl-out\\ORCH-SHIP\\render_ship.ps1`
invokes:

    stack <subject> --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure -o <out>

So the gallery the owner called horrible **is the pyramid path** -- the same
path another lane has just measured as having **no interior ring at all**
(monotonic from d=1 to d=275 px on `flower-bud`, against 12.65% on the estimator
arm). The bright ring is therefore **not** what he is reacting to. That
reframing is the practical value of this section: the loudest remaining defect
is softness, and there was an unwired sharpness module sitting next to it.

### 54.6 Disposition

Wiring is with the module's author; **independent verification of the module
itself is with a separate agent, dispatched in the same minute**, because the
author has never had an independent reader and I am not willing to put an
unverified restoration on a default path. The two run in parallel and I have
told the author not to land a default-on change until the verifier reports, and
to bring me any disagreement rather than settling it between themselves.

The guard that matters is pre-registered: **a Wiener FIR overshoots at edges,
and an overshoot at a silhouette is a halo.** The current pyramid profile is
monotonic to 275 px. If restoration puts a local maximum back into it, it is not
shippable at that strength regardless of how good its MTF numbers look, and what
I want back is the trade curve rather than a single operating point.
"""


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    if ANCHOR in text:
        print("already present; no change")
        return 0
    if not text.endswith("\n"):
        text += "\n"
    DOC.write_text(text + SECTION.lstrip("\n"), encoding="utf-8")
    print(f"appended; file now {len(DOC.read_text(encoding='utf-8'))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
