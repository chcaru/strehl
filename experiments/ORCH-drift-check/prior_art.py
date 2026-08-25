"""prior_art.py -- find the prior reports on a subject BEFORE commissioning it.

AGENTS rule 40 requires searching `docs/research/` for the question before
dispatching a milestone, and naming the prior reports in the brief. ORCH broke
that twice in one night:

  * M115 (deconvolution) was briefed citing none of M19/M20/M41/M70 -- and M41
    had ALREADY killed the idea on the noise axis.
  * M123 (outlier mask) was briefed citing none of M28/M60/M89/M97r -- three of
    which had already used real captures, and one of which had DERIVED why the
    answer must be no. The answer was additionally sitting in `outlier.rs` as a
    regression test whose NAME was the answer.

Both misses were mechanical and both were preventable in under a minute. This is
that minute.

    python prior_art.py outlier mask robustness
    python prior_art.py deconvolution wiener
    python prior_art.py --commission          # self-test, exits 1 on failure

Ranking is deliberately crude: a hit in a report's H1 headline is worth far more
than a hit in its body, because the headline is what the author chose to claim.
Verdict lines are surfaced because a prior REFUSAL is the single most
dispatch-relevant sentence a prior report can contain.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESEARCH = os.path.join(ROOT, "docs", "research")
CRATES = os.path.join(ROOT, "crates")

# Sentences that mean "someone already decided not to do this".
REFUSAL = re.compile(
    r"(should not ship|do not ship|do not wire|did not build|NO-GO|"
    r"declin\w+ to ship|not worth building|REFUTED|NOT SUPPORTED|"
    r"recommend(?:s|ed)? against)",
    re.I,
)

SKIP = {"the", "a", "an", "of", "and", "or", "is", "it", "to", "for", "on", "in"}


def collapse(s):
    """Whitespace-collapse so a phrase that wraps a line still matches."""
    return re.sub(r"\s+", " ", s)


def score_report(path, terms):
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    flat = collapse(raw).lower()

    m = re.search(r"^#\s+(.*)$", raw, re.M)
    headline = m.group(1).strip() if m else "(no h1)"
    head_l = headline.lower()

    body_hits = sum(flat.count(t) for t in terms)
    head_hits = sum(head_l.count(t) for t in terms)
    if body_hits == 0 and head_hits == 0:
        return None

    # A headline hit is worth 40 body hits: it is what the author claimed.
    score = head_hits * 40 + body_hits

    refusals = []
    for line in raw.split("\n"):
        s = line.strip()
        if not s or len(s) > 400:
            continue
        low = s.lower()
        if REFUSAL.search(s) and any(t in low for t in terms):
            refusals.append(collapse(s.lstrip("#*->| ").strip()))

    return {
        "name": os.path.basename(path),
        "headline": headline,
        "score": score,
        "head_hits": head_hits,
        "body_hits": body_hits,
        "refusals": refusals[:3],
    }


def scan_source(terms):
    """A test whose NAME is the answer is the cheapest prior art there is."""
    out = []
    for base, _dirs, files in os.walk(CRATES):
        if "target" in base:
            continue
        for fn in files:
            if not fn.endswith(".rs"):
                continue
            p = os.path.join(base, fn)
            with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    s = line.strip()
                    low = s.lower()
                    if not any(t in low for t in terms):
                        continue
                    if re.match(r"^\s*(fn |pub fn |async fn )", s) or "fn " in s[:12]:
                        out.append((os.path.relpath(p, ROOT), i, s[:150]))
                    elif re.search(r"MEASURED FAILURE|does_not_|_is_a_|REFUTED", s):
                        out.append((os.path.relpath(p, ROOT), i, s[:150]))
    return out


def run(terms, quiet=False):
    terms = [t.lower() for t in terms if t.lower() not in SKIP]
    if not terms:
        print("no usable search terms")
        return []
    reports = []
    for fn in sorted(os.listdir(RESEARCH)):
        if not fn.endswith(".md") or fn == "SYNTHESIS.md":
            continue
        r = score_report(os.path.join(RESEARCH, fn), terms)
        if r:
            reports.append(r)
    reports.sort(key=lambda r: -r["score"])

    if quiet:
        return reports

    print("terms: %s" % ", ".join(terms))
    print("=" * 78)
    top = [r for r in reports if r["head_hits"]] or reports[:8]
    if not top:
        print("NO PRIOR REPORTS. This subject appears genuinely unasked.")
    else:
        print("CITE THESE IN THE BRIEF (rule 40):\n")
        for r in top[:10]:
            flag = "  <-- HEADLINE MATCH" if r["head_hits"] else ""
            print("  %-36s score %5d%s" % (r["name"], r["score"], flag))
            print("      %s" % r["headline"][:104])
            for ref in r["refusals"]:
                print("      !! PRIOR REFUSAL: %s" % ref[:150])
        others = [r for r in reports if r not in top[:10]][:6]
        if others:
            print("\n  also mentions it: %s" % ", ".join(o["name"] for o in others))

    src = scan_source(terms)
    if src:
        print("\nIN THE SOURCE (a test name can be the whole answer):")
        for p, i, s in src[:12]:
            print("  %s:%d  %s" % (p, i, s))
    print("=" * 78)
    return reports


def commission():
    """Two positives with known answers, and a negative. Exit 1 on any failure."""
    ok = True

    def names(terms):
        return [r["name"] for r in run(terms, quiet=True)]

    # POSITIVE 1 -- the M123 miss. All four must surface.
    got = names(["outlier", "mask", "robustness"])
    want = ["M28", "M60", "M89", "M97r"]
    missing = [w for w in want if not any(n.startswith(w) for n in got)]
    if missing:
        ok = False
        print("FAIL positive-1: did not surface %s" % missing)
    else:
        print("PASS positive-1: M28/M60/M89/M97r all surfaced for the outlier mask")

    # POSITIVE 2 -- the M115 miss. M41 is the one that had already killed it.
    got = names(["deconvolution"])
    if not any(n.startswith("M41") for n in got):
        ok = False
        print("FAIL positive-2: M41 not surfaced for 'deconvolution'")
    else:
        print("PASS positive-2: M41 surfaced for 'deconvolution'")

    # NEGATIVE -- an absent subject must not be dressed up as prior art.
    got = names(["zirconium", "tuba"])
    if got:
        ok = False
        print("FAIL negative: invented subject returned %d reports" % len(got))
    else:
        print("PASS negative: an unasked subject returns nothing")

    print("\n%s" % ("COMMISSIONED - GREEN" if ok else "NOT COMMISSIONED - RED"))
    return 0 if ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--commission":
        sys.exit(commission())
    run(args)
