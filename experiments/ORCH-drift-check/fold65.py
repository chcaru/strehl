"""Fold the resolution non-finding and the demosaic identification.
Facts 1377-1378, discipline 686.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1377, "**THE PIPELINE DOES NOT MERGE AT HALF RESOLUTION AND UPSCALE; THE OUTPUT IS GENUINELY FULL SENSOR "
           "RESOLUTION.** MEASURED at `d3a49e4`. The sidecar's `plane 3516x2344` against a `7032 x 4688` output "
           "invites the reading that the merge runs binned and doubles on the way out. It does not: **3516x2344 "
           "is the size of each CFA plane**, which at 7032x4688 sensels is exactly correct, and the render log "
           "states `7032 x 4688 ... Malvar-He-Cutler demosaic`. `write_binned` -> `write_rgb16` emits at its "
           "input dimensions with no scaling (`image_out.rs`).",
     "**Retired hypothesis, recorded because it would otherwise resurface and because it would have dominated "
     "everything if true.** A hidden 2x upscale would mean every 100% crop examined tonight was really a 200% "
     "crop, that the delivered image had half the linear resolution it claimed, and that M85's `-0.2360` dex "
     "kernel attribution had been measured on already-interpolated data. **The reading was plausible from the "
     "sidecar alone and wrong**; the render log settled it in one line. General form: a dimension in a sidecar "
     "describes the stage that wrote it, not the pipeline's output -- **`plane` is per CFA plane, and a "
     "four-plane CFA is half-size on each axis by construction.**",
     "ORCH (MEASURED at `d3a49e4`; `ORCH-kernel/bee-3-cpl-catmull-rom.log`, `image_out.rs`)"),

    (1378, "**THE SHIPPED `--srgb` PATH DEMOSAICS WITH MALVAR-HE-CUTLER, AND A DEMOSAIC-FREE COMPARISON ARM "
           "ALREADY EXISTS.** MEASURED at `d3a49e4` from the render log: `Malvar-He-Cutler demosaic` on the "
           "default path. `--binned` skips demosaic entirely (one RGB pixel per 2x2 quad, no interpolation "
           "between CFA sites) and is mutually exclusive with `--demosaic`. Separately: `image_out.rs` defines "
           "`COSITE_SHIFT` and `develop_binned` displaces **red by (+d,+d) and blue by (-d,-d)** -- but that "
           "code is on the **binned path only** and cannot explain fringing in a default render.",
     "**Names the leading candidate for the observed magenta/cyan fringing and hands it a one-flag "
     "discriminator.** Malvar-He-Cutler is a 5x5 linear gradient-corrected demosaic whose principal documented "
     "failure mode is colour fringing at high-contrast edges, worst where the edge runs diagonally to the CFA "
     "lattice -- which describes a bee hair exactly. **The registered hazard is that the obvious control is "
     "itself uninspected:** `--binned` is the natural demosaic-free arm, but it routes through the very "
     "`COSITE_SHIFT` displacement whose sign convention would, if wrong, inject opposite-diagonal red/blue "
     "offsets -- precisely the artifact being hunted -- into the control. A control with an uninspected "
     "correction inside it is not a control.",
     "ORCH (MEASURED at `d3a49e4`; routed to M107 with the red herring flagged)"),
]

DISCIPLINES = [
    (686, "**A dimension in a sidecar or log describes the stage that wrote it, not the pipeline's output.** "
          "`plane 3516x2344` beside a `7032x4688` render reads as a 2x upscale and is not one -- a four-plane "
          "CFA is half-size on each axis by construction. Resolve any such apparent discrepancy against the "
          "**writer's own log line**, which states the emitted geometry directly, before inferring a resampling "
          "step that would invalidate every measurement taken downstream of it. Fact 1377."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1376 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^685\. ", l))
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
    print(f"folded facts 1377-1378 after line {fact_idx}, discipline 686 after line {disc_idx}")


if __name__ == "__main__":
    main()
