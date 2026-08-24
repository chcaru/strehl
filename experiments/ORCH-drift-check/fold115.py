"""Fold M109's landed preflight fix and the producer spec's transferable lessons.

Facts 1524-1525, disciplines 782-784.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1523 |")
disc_line = full_line(raw, "781. ")

NEW_FACTS = [
    (
        1524,
        "MEASURED",
        "M109",
        "**An invalid optical-profile key now fails in 0.235 s instead of 53.4 s -- a 227x "
        "faster failure, landed in `d142783`.** `preflight_ca_profile()` "
        "(`align_cmd.rs:288`) is called from both `align_cmd::run` and `merge_cmd.rs:1360`, "
        "beside the existing `--n-eff-map` refusal, and reports `unknown lateral-CA profile "
        "\"...-TYPO\"; known profiles: a7c2-fe100gm-2xtc-x4cpl`. Valid and unset keys are "
        "unchanged at exit 0 (56.2 s); byte-freeze **5/5 PASS** under "
        "`STREHL_FREEZE_REQUIRE=1`. **The cost was never the parse -- only when the error "
        "arrived**: `active_profile()` resolved per frame inside `warp_frame_in_place`, so "
        "a typo read as a slow arm rather than a config error, which in a comparison matrix "
        "is a silent corruption of the experiment. The per-frame re-read is a deliberate "
        "contract (`optics.rs:469`) and the fix caches nothing, so that contract survives. "
        "ORCH verified the commit touches only M109's two owned files.",
    ),
    (
        1525,
        "ARGUED",
        "M109",
        "**A post-warp saturation test under-counts exactly where the defect lives.** "
        "Catmull-Rom over a **fully** pinned neighbourhood reproduces the maximum, but over "
        "a **partially** pinned one it returns fractionally **less** than "
        "`CONTAINER_MAX_DN` -- so testing `>= CONTAINER_MAX_DN` after the warp misses "
        "saturated samples at **edges**, which is precisely where the residual magenta "
        "fringe is. Detect saturation **pre-warp on the sensel**, where the value is exact. "
        "If only the post-warp value is reachable at the accumulation site, use the exact "
        "`>=` test and record the edge under-count as **known, bounded, directional** "
        "conservatism.",
    ),
]

NEW_DISCS = [
    (
        782,
        "**Numerator and denominator must carry the same weights.** M109's B15 bar "
        "predicted ~74.7 % and measured 21.02 % because it counted over all sampled frames "
        "while the merge averages ~55 focus-gated contributors (facts 1502, 1503). The "
        "same error is now forbidden by construction in the shipped accumulator: the "
        "clip-state count uses **the identical `w_i` the value accumulator uses**. An "
        "unweighted count over a gate-weighted merge is not a noisier rate, it is **a "
        "different quantity** -- and inside shipped code that is far harder to notice than "
        "it was in a report.",
    ),
    (
        783,
        "**A producer exposes its sufficient statistics, never their ratio.** The merge "
        "accumulator returns `w_pinned` and `sum_w` separately rather than the fraction, "
        "because publishing the ratio silently moves the threshold policy from the "
        "consumer, which must defend it, into the producer, which cannot. The general "
        "form: **emit what was measured, not what a decision needs**, so that a later "
        "change of policy does not require a change of instrument.",
    ),
    (
        784,
        "**Prefer a known, bounded, directional bias over an epsilon's unknown one.** "
        "Facing an interpolation-induced under-count at edges, the tempting fix is a small "
        "tolerance on the saturation test. That converts a bias whose sign, cause and "
        "magnitude are all understood into one whose behaviour depends on an unjustified "
        "constant -- exactly the class Section 4.1 demolished. **Take the conservative "
        "test and write the limitation down** (fact 1525), so it can be measured later "
        "rather than discovered later.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
