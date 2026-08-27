"""check_readme.py -- test the gallery README's claims against the artifacts.

Last time I wrote a report, my own replacement text restated a refuted figure
while describing why it was refuted, and only a harness that asserted the string
was ABSENT caught it.  So this file does the same job for DELIVER-V5: every
load-bearing number in the shipped README is looked up in the log that produced
it, or counted on disk.  A README is a claim; a claim that nothing conditions on
is a defect this project has shipped repeatedly.

Usage:  python check_readme.py
"""
import json
import os
import re
import sys

DST = r"C:\dev\strehl-out\DELIVER-V5"
HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
_ok, _bad = [], []


def chk(tag, cond, msg):
    (_ok if cond else _bad).append(tag)
    print("  [%s] %-26s %s" % ("PASS" if cond else "FAIL", tag, msg))


def log(name):
    with open(os.path.join(LOGS, name), encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    rd = open(os.path.join(DST, "README.md"), encoding="utf-8").read()
    man = json.load(open(os.path.join(DST, "manifest.json"), encoding="utf-8"))

    print("=== counts on disk vs what the README claims ===")
    ncrop = len([f for f in os.listdir(os.path.join(DST, "crops-1to1"))
                 if f.endswith(".png")])
    nover = len([f for f in os.listdir(os.path.join(DST, "overview"))
                 if f.endswith(".png")])
    chk("crops-on-disk", ncrop == 78 and "78 crops" in rd,
        "%d crop PNGs on disk, README says 78" % ncrop)
    chk("overviews-on-disk", nover == 26 and "26 whole frames" in rd,
        "%d overview PNGs on disk, README says 26" % nover)
    chk("manifest-consistent",
        len(man["images"]) == nover
        and sum(len(m["crops"]) for m in man["images"]) == ncrop,
        "manifest lists %d images and %d crops"
        % (len(man["images"]), sum(len(m["crops"]) for m in man["images"])))
    chk("what-stacking-does",
        os.path.isdir(os.path.join(DST, "what-stacking-does"))
        and len(os.listdir(os.path.join(DST, "what-stacking-does"))) == 3,
        "carried forward, 3 files")
    chk("known-defects",
        any(f.endswith(".png") for f in os.listdir(os.path.join(DST, "known-defects"))),
        "the dust evidence file ships")

    print("\n=== every claimed number is in the log that produced it ===")
    v = log("verify.txt")
    chk("rim-zero", "0.000000000" in v and "max 0.000000000" in v
        and "0.000000000 DN" in rd,
        "verify.txt reports max rim 0.000000000 DN and the README states it")
    chk("neg-control", "caught 104 + missed 0" in v and "104 of 104" in rd,
        "104 of 104 planted corruptions caught")
    chk("byte-equality", "re-derivable from its master" in v,
        "verify.txt asserts byte equality, not closeness")

    c = log("commission-rim.txt")
    m = re.search(r"pass (\d+) \+ fail (\d+) = (\d+) of (\d+)", c)
    chk("commission-36", bool(m) and m.group(1) == "36" and m.group(2) == "0"
        and "36 arms" in rd,
        "commissioning partition %s, README says 36 arms" % (m.group(0) if m else "?"))
    chk("nearest-arm", "182.312" in c and "182.312 DN" in rd,
        "the nearest-neighbour arm -- the one that cannot ring -- is in the log")
    chk("blind-declared", "BLIND TO BLUR BY DESIGN" in c
        and "not a claim that the image is sharp" in rd,
        "the blindness is declared in both")
    chk("overview-limit", "1.000 DN" in c and "68.062" in c
        and "1.000 DN" in rd and "68.062 DN" in rd,
        "the 4x reduction's resolution limit AND the probe's non-triviality")

    x = log("crosscheck.txt")
    for want in ("17.1256", "36.9970", "13.4237"):
        chk("crosscheck-" + want, want in x and want in rd,
            "%s appears in crosscheck.txt and in the README" % want)
    r = log("resolve-min.txt")
    chk("min-resolved", "1.9619" in r and "1.9619" in rd
        and "DEFINITIONAL" in r,
        "the one disagreement is resolved to a definition in both")

    d, df, dp = log("dust.txt"), log("dust-flat.txt"), log("dust-patch.txt")
    chk("dust-underpowered", "UNDERPOWERED" in df
        and "underpowered, not negative" in rd.lower(),
        "the whole-frame arms are called underpowered in both")
    chk("dust-not-reproduced", "NOT REPRODUCED" in dp and "-0.78%" in dp
        and "0.78%" in rd,
        "the decisive arm's -0.78%% is in the log and the README")
    chk("dust-14of14", "flat+bright subjects at this site: 14 of 26" in dp
        and "14 of 26" in rd, "14 of 26 flat+bright subjects, both places")
    chk("dust-ratios", "1.34x" in d and "1.34x" in rd
        and "1.17x" in df and "1.60x" in df,
        "the null ratios are in the logs and the README")

    print("\n=== claims the README must NOT make ===")
    # Checked on the UNWRAPPED text with a context window, not line by line.
    # Line-based presence matching cannot distinguish a claim from its own
    # denial, and on a wrapped markdown file the denial is routinely on the
    # previous line -- my first draft of this check fired on
    #   "That does **not** establish that this stacker's / merge is halo-free"
    # which is the opposite of the claim it was hunting. That is the second
    # time today a presence-based grep has raised a false alarm on correct text.
    flat = re.sub(r"\s+", " ", rd)
    for bad, why in (
        (r"halo[- ]free", "this gallery does not measure the merge"),
        (r"\bproves the (merge|stack)", "the rim statistic cannot say that"),
        (r"dust (is|was) (absent|clean|fixed)", "not established; arms were underpowered"),
    ):
        unqualified = []
        for mm in re.finditer(bad, flat, re.I):
            ctx = flat[max(0, mm.start() - 140):mm.end() + 40].lower()
            if not re.search(r"\bnot\b|\bnever\b|\bcannot\b|\bdoes not\b", ctx):
                unqualified.append(ctx[-80:])
        chk("absent:" + bad[:18], not unqualified,
            "%d occurrence(s), all negated -- %s" % (
                len(re.findall(bad, flat, re.I)), why) if not unqualified
            else "UNQUALIFIED: ...%s" % unqualified[0])

    # A relaxed check must be shown to still convict. Plant the sentence the
    # README must never contain and require the same filter to fire on it.
    print("\n=== positive control: the relaxed filter must still convict ===")
    planted = flat + " The merge in this stacker is halo-free at every scale."
    fired = []
    for mm in re.finditer(r"halo[- ]free", planted, re.I):
        ctx = planted[max(0, mm.start() - 140):mm.end() + 40].lower()
        if not re.search(r"\bnot\b|\bnever\b|\bcannot\b|\bdoes not\b", ctx):
            fired.append(ctx[-60:])
    chk("filter-can-convict", len(fired) == 1,
        "planted an unqualified 'halo-free' claim: filter fired %d time(s)"
        % len(fired))
    print("  pass %d + fail %d = %d of %d   %s"
          % (len(_ok), len(_bad), len(_ok) + len(_bad), len(_ok) + len(_bad),
             "OK" if True else ""))
    if _bad:
        print("  FAILED: %s" % ", ".join(_bad))
    print("\nVERDICT: %s" % (
        "every load-bearing number in the shipped README is traceable to the log "
        "that produced it, and the counts match the files on disk"
        if not _bad else "the README claims something the artifacts do not support"))
    return 0 if not _bad else 1


if __name__ == "__main__":
    sys.exit(main())
