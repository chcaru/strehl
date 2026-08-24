"""Fold what the exposure patch measured. Facts 1348-1350, disciplines 669-670.

The patch is applied and proven inert on the measurement path. Two things came
out of running M100's own bars that are worth more than the patch itself: the
byte-freeze is broken at HEAD by something that is not M100, and the gallery
the owner has been judging was a numpy post-process rather than the program.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1348, "**THE EXPOSURE WIRING IS APPLIED AND SHIPPED AT `925d03d`, AND EVERY ONE OF M100's STRUCTURAL BARS "
           "PASSES AT CURRENT HEAD.** MEASURED on `bee-3-cpl --limit 60`: `cargo test -p strehl-core color::` "
           "**24 passed**, `cargo test -p strehl-cli --bins` **59 passed** -- both exactly the counts M100 "
           "pre-registered. `--exposure` without `--srgb` **refuses, exit 1**; `--exposure` together with "
           "`--auto-exposure` **refuses, exit 1**. Bar B2: `--srgb --exposure 0` is **SHA-256 identical** to "
           "`--srgb` alone (`EBBB8A26...714ED3`). Bar B3: `--srgb --auto-exposure` is **SHA-256 identical** to "
           "`--srgb --exposure=1.48` (`C57D5DDC...4AF29D6`).",
     "**The chosen exposure is `+1.48` stops, the identical number M100 recorded before M95, M97, M86c and M87 "
     "landed -- so the decision reproduces even though the bytes no longer do.** That is the stronger result: an "
     "order statistic of the merged image survived four intervening changes to the merge. Two of M100's four "
     "`main.rs` anchors had to be re-derived by hand because **the orchestrator invalidated them at `56bd846`** "
     "when applying M95, which appended to the doc comment and inserted `binned,` into the `Stack` destructure; "
     "the nine `merge_cmd.rs` hunks applied verbatim, each anchor located exactly once. The M95 interaction M100 "
     "flagged was **ruled ACCEPTED**: widening `if let Some(m) = matrix` lets `--srgb --exposure` reach the cosite "
     "resample on an uncharacterised camera, which is geometrically correct and unreachable on this corpus.",
     "ORCH (MEASURED at `925d03d`: `m100_bars.ps1`); M100's patch, applied"),

    (1349, "**THE BYTE-FROZEN MEASUREMENT PATH IS NOT FROZEN. IT MOVED BETWEEN M100's BASELINE AND HEAD, AND THE "
           "EXPOSURE PATCH IS PROVEN NOT TO BE THE CAUSE.** M100 recorded the default no-flag render of "
           "`bee-3-cpl --limit 60` as `54A5E20F...B37E7A2` **for three separate binaries** spanning a pre-M87 HEAD, "
           "`894f9f7`, and `894f9f7`+M100. The identical command at `925d03d` gives `CF266004...94B868`. All four "
           "of M100's recorded absolute hashes failed.",
     "**Negative control, run before accepting the convenient explanation:** the pre-patch `main.rs` and "
     "`merge_cmd.rs` were restored from `$env:TEMP`, **both touched so cargo could not serve a stale binary**, "
     "rebuilt `--release`, and re-measured. Pre-patch `CF266004...94B868`, post-patch `CF266004...94B868` -- "
     "**identical**, so the exposure patch does not touch this path, exactly as M100's hunk 8 was designed to "
     "guarantee. The break therefore predates it. ARGUED, dispatched to M106 rather than assumed: `885e9f7` wired "
     "alignment into `strehl stack` and is the likely cause and a defensible one. **The sharp case is M87**, whose "
     "`52c6a52` shipped the halo correction **\"default OFF\"** -- a falsifiable claim that is false if that commit "
     "moved this hash. Until attributed, every corpus number measured before the break describes a different "
     "program from every number measured after it.",
     "ORCH (MEASURED: `freeze_control.ps1`, restore-touch-rebuild); attribution dispatched to M106"),

    (1350, "**THE GALLERY THE OWNER HAS BEEN JUDGING WAS A NUMPY POST-PROCESS, NOT THE PROGRAM.** `gallery.py` "
           "renders with `--srgb --demosaic` -- which at the time could not expose -- and then applies its own gain "
           "in linear light at `TARGET = 0.92`, with a bisected clip budget, before writing the PNGs. Every "
           "`-exposed.tif`, every preview, every 100 % crop and the contact sheet carry that gain. **The tool's own "
           "target, measured and shipped by M100, is `0.90`.**",
     "So the images used to answer *does this look good* showed an output `strehl` could not produce, and the two "
     "targets would have **double-exposed** the moment the wiring landed. Corrected at `925d03d` by `gallery2.py`, "
     "which invokes `--srgb --auto-exposure` and post-processes nothing: the gain is the tool's, reported from the "
     "tool's own stderr. The same script also emits a **fixed centre crop beside the detail crop**, because "
     "discipline 666's biased selector was still choosing where to look.",
     "ORCH (MEASURED: read of `gallery.py` lines 63, 115-131 against `color.rs`)"),
]

DISCIPLINES = [
    (669, "**When a recorded absolute hash fails, restore the pre-change source, touch it, rebuild, and measure "
          "whether your own change is the cause -- before accepting any explanation, however plausible.** Four "
          "recorded hashes failed at once and a good story was available immediately: M95, M97, M86c and M87 had "
          "all landed since, and one of them wires alignment into the very path in question. The story was correct, "
          "and believing it would still have been wrong, because **the byte-freeze is the bar that exists precisely "
          "to not be argued away.** The control cost two 30-second rebuilds and converted *probably not me* into "
          "`CF266004...94B868 == CF266004...94B868`. Note the trap it had to route around: `Copy-Item` preserves "
          "the source mtime, so an untouched restore leaves cargo serving the binary you were trying to replace. "
          "Facts 1348, 1349."),
    (670, "**A gallery must render what the tool emits. If a script post-processes the output before the owner "
          "sees it, the owner is judging a program that does not exist.** `gallery.py` applied its own 0.92 gain on "
          "top of an un-exposed render for the whole period in which the owner said *those stacks don't look too "
          "good yet* -- so the verdict, the fix and the measurement were each about a slightly different image. "
          "**Any deviation between what is rendered and what is shown must be either eliminated or printed next to "
          "the picture.** Fact 1350."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1347 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^668\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1348-1350 after line {fact_idx}, "
          f"disciplines 669-670 after line {disc_idx}")


if __name__ == "__main__":
    main()
