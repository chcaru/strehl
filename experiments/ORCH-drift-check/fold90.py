"""Fold the unwired-subsystem inventory: ~2500 lines the render never touches."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1449,
     "**THREE MEASURED, TESTED SUBSYSTEMS TOTALLING ~2 500 LINES HAVE NO CONSUMER IN THE RENDER PATH, "
     "AND ONE OF THEM IS THE OWNER'S OWN GEAR PROFILE.** Inventory across all 52 workspace `.rs` files "
     "(`experiments/ORCH-drift-check/unwired.py`): of 146 top-level `pub fn`/`pub const` names, **50 "
     "have no reference outside their defining file.** Triaged, three are whole subsystems rather than "
     "internal helpers. **`optics.rs` (600 lines): every reference to `OpticalProfile`, `compose`, "
     "`by_key` and `A7C2_FE100GM_2XTC_X4CPL` -- the measured profile for the owner's A7C II + FE 100 GM "
     "+ 2x TC + X4 CPL -- is inside `optics.rs` itself.** Its only six external mentions are the words "
     "\"optics\" in unrelated comments plus `lib.rs:22 pub mod optics;`. **`photometric.rs` (1 365 "
     "lines)** and **`robust.rs` (544 lines)**: referenced only from `lib.rs` and from `examples/` "
     "binaries, never from `stack` or `merge`. **Positive controls in the same run: `flat_ratio` and "
     "`clip` resolve correctly as WIRED** -- real `use strehl_core::flat_ratio::{self, FrameFlat}` and "
     "`strehl_core::clip::CONTAINER_MAX_DN` imports with live call sites -- so the method distinguishes "
     "wired from unwired rather than reporting everything unwired.",
     "**This is the mechanism behind the owner's complaint that the stacks do not look good: the work "
     "is real and it is not reaching his photograph.** Note what the three are. `photometric` is "
     "per-frame gain and offset; `robust` is outlier rejection; both are items 1 and 2 of the reviewer's "
     "\"unglamorous layer SOTA dies without\", and the project built both and wired neither. `optics` is "
     "the pluggable camera-and-lens profile the owner asked for **by name in the founding request**, "
     "measured to `R^2 = 0.9969` (fact 1414), connected to nothing. This is the same shape as fact 1346 "
     "(the exposure machinery, *\"shipped, tested and unwired\"*, since wired) and fact 1414's lateral "
     "CA -- **so it is a recurring class, not three accidents**, which is why it now has an instrument "
     "and discipline 732 rather than three separate corrections.",
     "ORCH `unwired.py` across 52 files, 2 positive controls (MEASURED)"),

    (1450,
     "**`pub` IN A LIBRARY CRATE DISABLES THE COMPILER'S ONLY DEFENCE AGAINST UNWIRED WORK.** `dead_code` "
     "does not fire on `pub` items in a lib crate, because they are public API by definition. So a "
     "`pub fn` that nothing calls is invisible to `cargo build`, to `cargo clippy -D warnings`, and to "
     "every test that does not happen to exercise it. **All three subsystems in fact 1449 were compiling "
     "clean, passing their own unit tests, and folded as measured results the whole time.**",
     "**Every green signal the project had was telling the truth about a subsystem that did nothing.** "
     "The tests passed because they called the code directly; the compiler was silent because `pub` "
     "means \"someone outside may call this\"; and the milestone reports were accurate because the "
     "measurements were real. **Nothing was lying -- there was simply no instrument asking the one "
     "question that mattered, which is whether the render calls it.** That is the same failure shape as "
     "fact 1448's C1 check: an absent question, not a wrong answer.",
     "ORCH, derived from rustc's documented `dead_code` behaviour + fact 1449's three clean-compiling "
     "subsystems (ARGUED from a MEASURED inventory)"),
]

DISCIPLINES = [
    (732,
     "**A feature is not shipped when it is measured and tested; it is shipped when the default render "
     "path calls it. Verify the call, do not assume it.** Facts 1449-1450: ~2 500 lines across three "
     "subsystems -- including the owner's own optical profile -- compiled clean, passed unit tests, and "
     "were folded as measured results while **no code in `stack` or `merge` referenced them**. `pub` "
     "suppresses `dead_code` in a lib crate, so the compiler cannot tell you. **Run "
     "`experiments/ORCH-drift-check/unwired.py` before claiming any capability exists**, and when "
     "accepting a milestone that adds one, require the report to name the call site in the default path "
     "or to state explicitly that it is deliberately opt-in and why."),
    (733,
     "**An inventory instrument needs a positive control as much as a measurement does -- otherwise "
     "\"nothing is wired\" and \"my grep is broken\" are the same output.** `unwired.py` was believable "
     "only because `flat_ratio` and `clip` came back **wired**, with real `use strehl_core::...` imports "
     "and live call sites, in the same run that reported `optics`, `photometric` and `robust` as "
     "orphans. **A tool that reports a problem everywhere is reporting itself.** The cheapest form of "
     "this control is to include, in the same run and by the same code path, an item you already know "
     "the answer for."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1448 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^731\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded facts 1449-1450, disciplines 732-733")


if __name__ == "__main__":
    main()
