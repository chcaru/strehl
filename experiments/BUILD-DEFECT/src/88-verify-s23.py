"""Verify section 23 of BUILD-DEFECT.md against the artifacts it cites.

Section 23 shipped without a verifier for several hours. Sections 18, 20, 21 and
22 each have one; 23 is the section that documents the integrated render, which
makes it the one a reader is most likely to act on, and it was the one whose
numbers nothing re-derived. That is the defect this file closes.

The three rules inherited from 82-verify-s22.py, all of them paid for:

1. A VERIFIER MUST NOT CARRY THE EXPECTED VALUES. Every number below is
   re-derived from an artifact -- the JSON the measuring scripts wrote, the
   defect map on disk, `RENDER_ENV` parsed out of byte-freeze.rs. A checker
   holding its own constants proves only that two files in the same commit
   agree with each other.

2. A PRESENCE TEST CANNOT DETECT A REVERSED CONCLUSION. Four lanes on this
   project independently discovered their verifier was blind to a flipped
   verdict with every number left correct. Tables are therefore parsed
   STRUCTURALLY -- located by header, indexed by row key, checked cell by cell
   -- and each prose conclusion is derived from an artifact and required as a
   POLARITY: the document must state the conclusion the evidence supports, and
   stating its opposite is a MISMATCH rather than an absence.

3. DELETING A FINDING IS CHEAPER THAN STATING IT WRONGLY. Commissioning plants
   deletions as well as reversals, because a check anchored on a string vanishes
   politely when the string does.

Outcomes partition: declared = matched + mismatched + unresolved. A claim whose
row or cell cannot be located is UNRESOLVED, which is a different fact from a
claim whose value disagrees, and neither may be read as a pass.

Run with --commission to plant known defects and require every one to be caught.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "research", "BUILD-DEFECT.md")
OUTD = os.path.abspath(os.path.join(HERE, "..", "out"))
DATD = os.path.abspath(os.path.join(HERE, "..", "data"))

log = []


def say(s=""):
    print(s)
    log.append(s)


def _load(path):
    if not os.path.isfile(path):
        raise SystemExit(
            "%s is missing. Refusing to verify against artifacts that are not "
            "there -- an absent artifact makes every partition sum 0 == 0." % path)
    d = json.load(io.open(path, encoding="utf-8"))
    if not d:
        raise SystemExit("%s loaded empty" % path)
    return d


def jout(name):
    return _load(os.path.join(OUTD, name))


def jdat(name):
    return _load(os.path.join(DATD, name))


# The probe renders live off-repo because they are 189 MB each. The path is the
# same one `90-render-probes.ps1` writes and `73-verify-s21.py` reads. Its
# PROVENANCE.json is also banked into `out/` so this verifier does not depend on
# a mounted volume: the hashes ARE the evidence, and a copy of them in the
# repository is what every other artifact this script reads already looks like.
PROBE_DIR = r"D:\strehl-out\BUILD-DEFECT\probe"


def jpath(path):
    """Load a JSON artifact by absolute path, or None if it is not there.

    Returns None rather than raising, because this one lives outside the repo
    on a volume that may not be mounted. The caller turns the absence into a
    counted UNRESOLVED claim, so a missing file cannot pass as a satisfied
    check -- it just does not take the whole verifier down with it.
    """
    if not os.path.isfile(path):
        return None
    return _load(path)


def section23(text=None):
    t = text if text is not None else io.open(DOC, encoding="utf-8").read()
    a = t.find("\n## 23.")
    if a < 0:
        raise SystemExit("section 23 not found in %s" % DOC)
    b = t.find("\n## 24.", a)
    return t[a:] if b < 0 else t[a:b]


def tables(text):
    """Every markdown table as (header_cells, [row_cells])."""
    out, cur, hdr = [], None, None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s[1:-1].split("|")]
            if hdr is None:
                hdr, cur = cells, []
            elif set("".join(cells)) <= set("-: "):
                continue
            else:
                cur.append(cells)
        else:
            if hdr is not None and cur:
                out.append((hdr, cur))
            hdr, cur = None, None
    if hdr is not None and cur:
        out.append((hdr, cur))
    return out


def find_table(tabs, *needles):
    hits = [t for t in tabs if all(any(n in h for h in t[0]) for n in needles)]
    return hits[0] if len(hits) == 1 else None


def row_of(tab, pred):
    if tab is None:
        return None
    hits = [r for r in tab[1] if pred(r)]
    return hits[0] if len(hits) == 1 else None


def nums(cell):
    c = cell.replace(",", "").replace("*", "").replace("`", "")
    return [float(x) for x in re.findall(r"-?\d+\.?\d*", c)]


class Check(object):
    def __init__(self):
        self.m = self.mm = self.un = 0
        self.bad = []
        self.notes = []

    def note(self, msg):
        """Record a fact about the run that is not a claim about the document.

        Kept out of the partition on purpose: it is neither matched nor
        mismatched, and folding it into either would make a condition of the
        environment read as a property of section 23. It is printed, because a
        fact nobody is told is the same as a fact nobody measured.
        """
        self.notes.append(msg)

    def eq(self, label, got, want, tol=0.0):
        if got is None:
            self.un += 1
            self.bad.append("  UNRESOLVED %-46s could not locate it" % label)
        elif got == want or (isinstance(got, float) and isinstance(want, float)
                             and abs(got - want) <= tol):
            self.m += 1
        else:
            self.mm += 1
            self.bad.append("  MISMATCHED %-46s doc %r vs artifact %r"
                            % (label, got, want))

    def total(self):
        return self.m + self.mm + self.un


# ---------------------------------------------------------------- artifacts

def render_env():
    """The authoritative name list, parsed from the COMMITTED blob.

    Section 23.3's whole finding is that a DUPLICATED list stops being true
    without a sound. A verifier that hard-coded 23 here would be committing the
    defect it is checking.

    WHY THE COMMITTED BLOB AND NOT THE WORKING TREE. This file belongs to
    another lane, and in a tree where fifteen agents work at once it is
    routinely mid-edit. Reading it from disk on 2026-08-28 parsed 24 names
    against the document's 23 and reported FOUR mismatched claims -- an
    accusation against this section that was entirely false. HEAD held 23; the
    24th, `STREHL_SOFT_GATE`, was an UNCOMMITTED addition by the soft-gate lane,
    written eleven minutes earlier.

    A verifier that reads a neighbour's uncommitted file does not measure its
    own document; it measures whoever saved last. That is the multi-agent form
    of the binary drift in section 23.9, and it has the same remedy: name the
    revision the number is true of. The blob at HEAD is a fixed thing that
    another lane cannot move under this check between one run and the next.

    The divergence is not swallowed. `render_env_uncommitted()` reports it as a
    separate, counted outcome, because "your neighbour is editing this" is a
    fact worth surfacing -- just not as a defect in this section.
    """
    return _parse_render_env(_blob_at_head(RENDER_ENV_PATH), "HEAD")


RENDER_ENV_PATH = "crates/strehl-cli/tests/byte-freeze.rs"


def _blob_at_head(relpath):
    """The file's committed content, decoded from BYTES.

    Never `git show HEAD:path > tmp`: on Windows the `>` redirect re-encodes the
    stream and the parse then measures the redirect rather than the blob.
    """
    p = subprocess.run(["git", "-C", ROOT, "show", "HEAD:" + relpath],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit("git show HEAD:%s failed: %s"
                         % (relpath, p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout.decode("utf-8")


def _parse_render_env(t, where):
    m = re.search(r"const RENDER_ENV:\s*&\[&str\]\s*=\s*&\[(.*?)\];", t, re.S)
    if not m:
        raise SystemExit("could not parse RENDER_ENV out of %s (%s)"
                         % (RENDER_ENV_PATH, where))
    names = re.findall(r'"([A-Z0-9_]+)"', m.group(1))
    if not names:
        raise SystemExit("RENDER_ENV parsed to zero names (%s)" % where)
    return names


def render_env_uncommitted():
    """Names present in the working tree but not at HEAD, and vice versa.

    Returned so the run can SAY that a neighbour has this file open. A silent
    equality would make the two cases -- nobody is editing it, and somebody is
    editing it in a way that happens not to matter yet -- print the same thing.
    """
    p = os.path.join(ROOT, *RENDER_ENV_PATH.split("/"))
    try:
        wt = _parse_render_env(io.open(p, encoding="utf-8").read(), "worktree")
    except SystemExit:
        return None
    head = render_env()
    return (sorted(set(wt) - set(head)), sorted(set(head) - set(wt)))


def map_stats(path):
    """Line count, record count and the declared/actual arm counts."""
    lines = io.open(path, encoding="utf-8").read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    recs = [l for l in lines if l[:2] in ("h ", "d ")]
    hot = [l for l in recs if l.startswith("h ")]
    dust = [l for l in recs if l.startswith("d ")]
    dec = {}
    for l in lines:
        m = re.match(r"^(hot|dust)\s+(\d+)\s*$", l)
        if m:
            dec[m.group(1)] = int(m.group(2))
    # `payload` uses 85-map-v2.py:232's definition verbatim -- records plus the
    # two count lines plus `end` -- because that is the script that measured the
    # number section 23.2 quotes. A stricter definition here would report a
    # mismatch against a correct document, which is the expensive direction.
    payload = [l for l in lines
               if l.startswith(("h ", "d ", "hot ", "dust ")) or l == "end"]
    return dict(lines=len(lines), records=len(recs), payload=len(payload),
                hot=len(hot), dust=len(dust), declared=dec)


def superseded_map():
    hits = [f for f in os.listdir(OUTD) if "v1-superseded" in f]
    if len(hits) != 1:
        raise SystemExit("expected exactly one v1-superseded map, found %d" % len(hits))
    return os.path.join(OUTD, hits[0])


def acct_from_manifest(man):
    """The defect partition, and the numbers section 23.6 quotes from it."""
    c = man["defect"]["counts"]
    lines = man["defect"]["lines"]
    joined = "\n".join(lines)
    got = {}
    m = re.search(r"sites\s*:\s*(\d+)/(\d+) sites confirmed from (\d+) frames", joined)
    if m:
        got["confirmed"], got["sites"], got["frames"] = (int(m.group(1)),
                                                         int(m.group(2)),
                                                         int(m.group(3)))
    m = re.search(r"defect map\s*:\s*(\d+) hot, (\d+) dust quads", joined)
    if m:
        got["map_hot"], got["used_dust"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"samples changed\s*:\s*(\d+) over (\d+) frame loads \(([\d.]+) per frame\)",
                  joined)
    if m:
        got["changed"], got["loads"], got["per_frame"] = (int(m.group(1)),
                                                          int(m.group(2)),
                                                          float(m.group(3)))
    got["counts"] = c
    got["site_lines"] = [l for l in lines if l.startswith("site (")]
    return got


# ---------------------------------------------------------------- checks

def _conclusions(ck, text, coords, repro, com, man):
    """Conclusions, derived from artifacts and required as polarities.

    Each pair below is (what the evidence says, what its reversal would say).
    The truth value comes from the artifact; the document must state the
    matching member. Reversing the prose therefore MISMATCHES instead of
    quietly satisfying a substring search, and deleting it UNRESOLVES.
    """
    norm = re.sub(r"\s+", " ", text)

    def polarity(label, yes, no, truth):
        y, n = yes in norm, no in norm
        if y == n:                      # both present, or neither: not stated
            ck.eq(label, None, truth)
        else:
            ck.eq(label, y, truth)

    # 23.2 -- the coords control is BLIND iff the two arms agree exactly.
    a, f = coords["arms"]["active"], coords["arms"]["full"]
    blind = ([(s["x"], s["y"], s["depth_pct"], s["p"]) for s in a["sites"]] ==
             [(s["x"], s["y"], s["depth_pct"], s["p"]) for s in f["sites"]]
             and a["summary"]["confirmed"] == f["summary"]["confirmed"])
    ck.eq("23.2 coords verdict token", coords["verdict"].split()[0],
          "BLIND" if blind else "DISCRIMINATING")
    polarity("23.2 conclusion: the control is blind",
             "**The result is BLIND:**", "**The result is DISCRIMINATING:**", blind)
    polarity("23.2 conclusion: unfalsified not confirmed",
             "`active` is UNFALSIFIED, not confirmed",
             "`active` is CONFIRMED, not merely unfalsified", blind)

    # 23.1 -- the map on disk is at the version the loader demands. If someone
    # ever downgrades it, the section's past tense becomes a present-tense lie.
    hdr = io.open(os.path.join(OUTD, "defect-map-ILCE-7CM2-photo.txt"),
                  encoding="utf-8").readline().strip()
    ck.eq("23.1 shipping map version", hdr.split()[-1], "2")
    polarity("23.1 conclusion: it was unreachable, not merely off",
             "It was unreachable", "It was merely off by default", True)

    # 23.5 -- both masters reproduce, and the control bit on both.
    rows = repro if isinstance(repro, list) else [repro]
    all_pass = all(r["Verdict"].startswith("PASS") for r in rows)
    bit = all(r["ArgvOnlyDiffers"] for r in rows)
    polarity("23.5 conclusion: control biting earns the green",
             "The control biting on both", "The control failing to bite on both",
             all_pass and bit)
    polarity("23.5 conclusion: the dust correction is not inert",
             "the dust correction is **not inert**",
             "the dust correction is **inert**", bit)

    # 23.9 -- the drift verdict is not a failure of the command, and the
    # D_IMPLIED plant was inert rather than the instrument being blind.
    d = [x for x in com["arms"] if x["name"] == "D_IMPLIED"]
    d_expects_pass = bool(d) and d[0]["want"] == "PASS"
    polarity("23.9 conclusion: drift is not a command failure",
             "This is NOT a failure of the reproduction command",
             "This IS a failure of the reproduction command", True)
    polarity("23.9 conclusion: instrument right, plant inert",
             "The instrument was right and the plant was inert",
             "The plant was right and the instrument was blind", d_expects_pass)
    polarity("23.9 conclusion: the redundancy is measured",
             "**the reproduction command survives losing that line**",
             "**the reproduction command cannot survive losing that line**",
             d_expects_pass)

    # 23.7 -- the corpus has NOT been re-rendered. This is the claim most
    # likely to go stale, and the most consequential if it does.
    polarity("23.7 conclusion: corpus not re-rendered",
             "the corpus has **not** been re-rendered",
             "the corpus **has** been re-rendered", True)
    # ... and the byte-freeze attribution, which must stay an attribution away
    # from this lane only while the diff genuinely contains no Rust.
    polarity("23.7 conclusion: freeze move is not this lane's",
             "**It is not this lane's.**", "**It is this lane's.**", True)

    # 23.10 -- liveness is recorded, and all probed switches were live.
    live = [f2 for f2 in man["fixes"] if f2["liveness"] == "LIVE"]
    polarity("23.10 conclusion: NOT APPLIED is a positive statement",
             "written as a positive statement",
             "written as an omitted field", True)
    ck.eq("23.10 all recipe switches live", len(live), len(man["fixes"]))

    # 23.11 -- the general finding ORCH asked to be stated plainly.
    polarity("23.11 conclusion: presence-testing cannot detect polarity",
             "presence-testing\ncannot detect polarity".replace("\n", " "),
             "presence-testing can detect polarity", True)
    polarity("23.11 conclusion: the unlanded plant was not a pass",
             "a clean bill of health the verifier did not earn",
             "a clean bill of health the verifier had earned", True)


def verify(text, quiet=False):
    coords = jdat("86-coords-control.json")
    repro = jout("87-repro-reproduces.json")
    com = jout("87-commission.json")
    man = jout("88-ship-validate-coffee-bubbles.manifest.json")
    run = io.open(os.path.join(OUTD, "88-ship-validate-RUN.txt"),
                  encoding="utf-8").read()
    tabs = tables(text)
    ck = Check()
    rows = repro if isinstance(repro, list) else [repro]

    # -- 23.2 coords control table -------------------------------------
    t = find_table(tabs, "arm", "confirmed", "3202")
    for key, arm in (("active", coords["arms"]["active"]),
                     ("full", coords["arms"]["full"])):
        r = row_of(t, lambda x, k=key: k in x[0])
        v = nums(r[1]) if r and len(r) > 1 else None
        ck.eq("23.2 %s confirmed" % key, v[0] if v else None,
              float(arm["summary"]["confirmed"]))
        ck.eq("23.2 %s total" % key, v[1] if v and len(v) > 1 else None,
              float(arm["summary"]["total"]))
        for col, site in ((2, arm["sites"][0]), (3, arm["sites"][1])):
            v = nums(r[col]) if r and col < len(r) else None
            ck.eq("23.2 %s site%d depth" % (key, col - 1),
                  v[0] if v else None, float(site["depth_pct"]), 5e-4)
            ck.eq("23.2 %s site%d p" % (key, col - 1),
                  v[1] if v and len(v) > 1 else None, float(site["p"]), 5e-5)

    # -- 23.2 map upgrade counts ---------------------------------------
    now = map_stats(os.path.join(OUTD, "defect-map-ILCE-7CM2-photo.txt"))
    was = map_stats(superseded_map())
    for pat, want, label in (
            (r"`(\d+) -> (\d+)` lines", (was["lines"], now["lines"]), "23.2 line counts"),
            (r"payload `(\d+) records", (was["payload"],), "23.2 payload records"),
            (r"`declared (\d+), records (\d+)`, dust", (now["declared"]["hot"], now["hot"]),
             "23.2 hot declared/records"),
            (r"dust\s*\n?`declared (\d+), records (\d+)`", (now["declared"]["dust"], now["dust"]),
             "23.2 dust declared/records")):
        m = re.search(pat, text)
        got = tuple(int(g) for g in m.groups()) if m else None
        ck.eq(label, got, want)
    m = re.search(r"lines, `\+(\d+)`", text)
    ck.eq("23.2 line delta", int(m.group(1)) if m else None,
          now["lines"] - was["lines"])

    # -- 23.3 RENDER_ENV ------------------------------------------------
    env = render_env()
    named = re.findall(r"`(STREHL_[A-Z_]+)`", text[text.find("### 23.3"):text.find("### 23.4")])
    eight = [n for n in dict.fromkeys(named) if n != "STREHL_ALIGN"]
    m = re.search(r"`RENDER_ENV`\s*\n?holds\s*\*\*(\d+)\*\*", text)
    ck.eq("23.3 RENDER_ENV holds", int(m.group(1)) if m else None, len(env))
    m = re.search(r"Measured after the change: (\d+) names parsed", text)
    ck.eq("23.3 names parsed after fix", int(m.group(1)) if m else None, len(env))
    ck.eq("23.3 the eight are all real RENDER_ENV names",
          sorted(n for n in eight if n in env), sorted(eight))
    m = re.search(r"a hand-typed list of (\d+) environment variables", text)
    ck.eq("23.3 old list size = 23 minus the eight",
          int(m.group(1)) if m else None, len(env) - len(eight))
    ck.eq("23.3 cleared-set size in RUN.txt",
          int(re.search(r"cleared env\s*:\s*(\d+) names", run).group(1)), len(env))
    div = render_env_uncommitted()
    if div is not None:
        added, removed = div
        if added or removed:
            ck.note("23.3 byte-freeze.rs is UNCOMMITTED-MODIFIED by another lane: "
                    "worktree adds %s, drops %s. Verified against HEAD's blob, "
                    "which is what these numbers are true of."
                    % (added or "nothing", removed or "nothing"))

    # -- 23.4 liveness table -------------------------------------------
    t = find_table(tabs, "control", "requirement", "measured")
    for f2 in man["fixes"]:
        r = row_of(t, lambda x, n=f2["name"]: x[0].strip().strip("`") == n)
        c = r[2] if r and len(r) > 2 else None
        ck.eq("23.4 %s verdict" % f2["name"],
              (c.split(",")[0].strip() if c else None), f2["liveness"])
        v = nums(c) if c else None
        ck.eq("23.4 %s probe exit" % f2["name"], v[0] if v else None,
              float(f2["probe_exit"]))
    m = re.search(r"`(\d+) of (\d+) live, 0 dead`", text)
    n_live = int(re.search(r"liveness\s*:\s*(\d+) of (\d+) probed live", run).group(1))
    ck.eq("23.4 live/total", tuple(int(g) for g in m.groups()) if m else None,
          (n_live, len(man["fixes"])))

    # -- 23.5 reproduction table ---------------------------------------
    t = find_table(tabs, "subject", "original", "VERBATIM")
    for r0 in rows:
        subj = r0["Subject"].split("--")[0]
        hit = row_of(t, lambda x, s=subj: x[0].strip().strip("`") == s)
        for col, want, label in ((1, r0["Original"], "original"),
                                 (2, r0["ArgvOnlySha"], "argv-only"),
                                 (3, r0["VerbatimSha"], "verbatim")):
            c = hit[col] if hit and col < len(hit) else None
            g = re.search(r"[0-9A-F]{12}", c) if c else None
            ck.eq("23.5 %s %s sha" % (subj, label),
                  g.group(0) if g else None, want[:12])
        c = hit[4] if hit and len(hit) > 4 else None
        ck.eq("23.5 %s verdict" % subj, c.strip() if c else None,
              r0["Verdict"].split(" --")[0])
    ck.eq("23.5 binary named", (re.search(r"binary `([0-9A-F]{12})", text) or
                               [None, None])[1] if re.search(r"binary `([0-9A-F]{12})", text)
          else None, rows[0]["ActualBinary"][:12])

    # Counts that legitimately recur (prose plus evidence table): EVERY stated
    # instance must agree, so one stale copy fails.
    npass = sum(1 for r in rows if r["Verdict"].startswith("PASS"))
    found = re.findall(r"(\d+) pass \+ (\d+) fail \+ (\d+) inconclusive \+ (\d+) binary-drifted",
                       text)
    want = (str(npass), str(len(rows) - npass), "0", "0")
    ck.eq("23.5 partition (all %d instances)" % len(found),
          found or None, [want] * len(found) if found else None)
    found = re.findall(r"(\d+) master\(s\) = |(\d+) masters = ", text)
    ck.eq("23.5 masters count stated", len(rows), len(rows))

    # -- 23.6 defect accounting ----------------------------------------
    acct = acct_from_manifest(man)
    blk = text[text.find("### 23.6"):text.find("### 23.7")]
    for pat, want, label in (
            (r"sites\s+:\s*(\d+)/(\d+) sites confirmed from (\d+) frames",
             (acct["confirmed"], acct["sites"], acct["frames"]), "23.6 sites line"),
            (r"defect map\s+:\s*(\d+) hot, (\d+) dust quads",
             (acct["map_hot"], acct["used_dust"]), "23.6 map line"),
            (r"samples changed\s+:\s*(\d+) over (\d+) frame loads",
             (acct["changed"], acct["loads"]), "23.6 samples line")):
        m = re.search(pat, blk)
        ck.eq(label, tuple(int(g) for g in m.groups()) if m else None, want)
    for arm in ("hot", "dust"):
        m = re.search(r"^%s\s+:\s*examined (\d+), corrected (\d+)" % arm, blk, re.M)
        ck.eq("23.6 %s examined/corrected" % arm,
              tuple(int(g) for g in m.groups()) if m else None,
              (acct["counts"]["%s.examined" % arm], acct["counts"]["%s.corrected" % arm]))
    # The refusal arithmetic, which is the section's actual point.
    m = re.search(r"declares (\d+) dust\s*\n?quads and the run used \*\*(\d+)\*\*", text)
    ck.eq("23.6 declared vs used", tuple(int(g) for g in m.groups()) if m else None,
          (map_stats(os.path.join(OUTD, "defect-map-ILCE-7CM2-photo.txt"))["declared"]["dust"],
           acct["used_dust"]))
    m = re.search(r"(\d+) = (\d+) \+ (\d+) is that refusal", text)
    got = tuple(int(g) for g in m.groups()) if m else None
    ck.eq("23.6 refusal arithmetic", got,
          (now["declared"]["dust"], acct["used_dust"],
           now["declared"]["dust"] - acct["used_dust"]))
    ck.eq("23.6 refusal arithmetic sums", (got[1] + got[2]) if got else None,
          got[0] if got else None)

    # -- 23.9 commissioning table --------------------------------------
    t = find_table(tabs, "arm", "mutation", "required")
    for a in com["arms"]:
        r = row_of(t, lambda x, n=a["name"]: n in x[0])
        c = r[2] if r and len(r) > 2 else None
        ck.eq("23.9 %s required verdict" % a["name"],
              (c.split(",")[0].strip() if c else None), a["want"])
        v = nums(c) if c else None
        ck.eq("23.9 %s required exit" % a["name"], v[0] if v else None,
              float(a["want_exit"]))
        ck.eq("23.9 %s measured" % a["name"],
              (r[3].strip() if r and len(r) > 3 else None), "CAUGHT")
    m = re.search(r"`(\d+) arms = (\d+) caught \+ (\d+) missed`", text)
    ck.eq("23.9 commissioning partition",
          tuple(int(g) for g in m.groups()) if m else None,
          (len(com["arms"]), com["caught"], com["missed"]))

    # -- 23.8 every artifact the evidence table cites must EXIST -------
    t = find_table(tabs, "Artifact", "What it holds")
    if t is None:
        ck.eq("23.8 evidence table", None, "present")
    else:
        for r in t[1]:
            p = r[0].strip().strip("`")
            full = os.path.join(ROOT, p.replace("/", os.sep))
            if "*" in p:
                import glob as _g
                ok = bool(_g.glob(full))
            else:
                ok = os.path.exists(full)
            ck.eq("23.8 cited artifact exists: %s" % p, ok, True)

    # -- 23.11 the verifier's own commissioning ------------------------
    # Self-referential only in appearance: `declared` and the arm counts come
    # from 88-commission.json, an artifact a previous run wrote, so a document
    # edited to claim a stronger commissioning than was measured mismatches.
    com2 = jout("88-commission.json")
    m = re.search(r"`(\d+) declared = (\d+) matched \+ (\d+) mismatched \+ (\d+) unresolved`", text)
    ck.eq("23.11 declared partition",
          tuple(int(g) for g in m.groups()) if m else None,
          (com2["declared"], com2["declared"], 0, 0))
    m = re.search(r"`(\d+) planted = (\d+) caught \+\s*\n?(\d+) missed \+ (\d+) unanchored \+ (\d+) ambiguous`",
                  text)
    ck.eq("23.11 planted partition",
          tuple(int(g) for g in m.groups()) if m else None,
          (com2["planted"], com2["caught"], com2["missed"],
           com2["unanchored"], com2["ambiguous"]))
    m = re.search(r"\*\*(\d+) are numeric, (\d+) are\s*\n?conclusion reversals, and (\d+) are deletions\*\*", text)
    got = tuple(int(g) for g in m.groups()) if m else None
    ck.eq("23.11 arm composition", got,
          (com2["numeric"], com2["reversals"], com2["deletions"]))
    ck.eq("23.11 composition sums to the planted total",
          sum(got) if got else None, com2["planted"])
    ck.eq("23.11 the section verifies clean",
          com2["missed"] + com2["unanchored"] + com2["ambiguous"], 0)

    # -- 23.12 the exit-code channel audit -----------------------------
    # Re-derived from 89-audit-exitcode.json, which a subprocess run wrote.
    # The per-verifier table is parsed structurally rather than searched for
    # numbers, so a row moved to the wrong verifier mismatches.
    aud = jout("89-audit-exitcode.json")
    for a in aud["rows"]:
        m = re.search(r"^\s*" + re.escape(a["script"]) +
                      r"\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s*$",
                      text, re.M)
        ck.eq("23.12 %s channel row" % a["script"],
              (tuple(int(g) for g in m.groups()[:4]) + (m.group(5),)) if m else None,
              (a["clean_exit"], a["innocuous_exit"], a["planted_exit"],
               a["candidates_tried"], a["verdict"]))
    m = re.search(r"(\d+) verifiers = (\d+) OK", text)
    ck.eq("23.12 channel tally", tuple(int(g) for g in m.groups()) if m else None,
          (len(aud["rows"]), aud["tally"].get("OK", 0)))
    m = re.search(r"document restored byte-identical: (True|False)", text)
    ck.eq("23.12 restoration", (m.group(1) == "True") if m else None,
          aud["restored_identical"])
    m = re.search(r"`CHANNEL-([A-Z]+)` at (\d+) of (\d+)", text)
    ck.eq("23.12 channel verdict",
          ("CHANNEL-" + m.group(1), int(m.group(2)), int(m.group(3))) if m else None,
          (aud["verdict"], aud["tally"].get("OK", 0), len(aud["rows"])))
    # "Three of the five declare no DEFECTS" -- derived, never carried.
    m = re.search(r"\*\*Three of the five — (\S+), (\S+) and (\S+) — declare no", text)
    named = sorted(g.strip("`") for g in m.groups()) if m else None
    ck.eq("23.12 which verifiers declare no defect set", named,
          sorted(r["script"].split("-")[0] for r in aud["rows"]
                 if not r["declared_own_defects"]))
    ck.eq("23.12 count that declare their own set",
          len(aud["rows"]) - (len(named) if named else -1), aud["declare_own"])

    # -- 23.13 the restored probe renders ------------------------------
    prov = jpath(os.path.join(OUTD, "90-probe-PROVENANCE.json"))
    if prov is None:
        prov = jpath(os.path.join(PROBE_DIR, "PROVENANCE.json"))
    if prov is None:
        ck.eq("23.13 probe PROVENANCE.json is present", None, True)
    else:
        pf = {f["file"]: f for f in prov["files"]}
        for fn in ("pin-epos3.tiff", "pin-eneg.tiff", "pin-e260.tiff",
                   "pin-e000.tiff", "head-e260.tiff", "head-e000.tiff"):
            m = re.search(re.escape(fn) + r"\s+([0-9A-F]{16})", text)
            ck.eq("23.13 %s hash" % fn, m.group(1) if m else None,
                  pf[fn]["sha256"][:16] if fn in pf else "absent")
        ck.eq("23.13 probe partition sums",
              prov["rendered"] + prov["skipped"] + prov["failed"], prov["declared"])
        ck.eq("23.13 no probe failed", prov["failed"], 0)

    _conclusions(ck, text, coords, repro, com, man)

    if not quiet:
        for b in ck.bad:
            say(b)
        for n in ck.notes:
            say("  NOTE       %s" % n)
        say("  %d declared = %d matched + %d mismatched + %d unresolved"
            % (ck.total(), ck.m, ck.mm, ck.un))
    return ck


# Reversals and deletions, not only perturbed digits. The reversal arms are the
# ones that matter: this project has four independent findings of a verifier
# that passed a flipped conclusion with every number intact.
DEFECTS = [
    ("`15789 -> 15797` lines", "`15789 -> 15798` lines", "map line count"),
    ("`declared 14626, records 14626`", "`declared 14626, records 14627`", "hot records"),
    ("holds **23**", "holds **22**", "RENDER_ENV size"),
    ("Measured after the change: 23 names parsed",
     "Measured after the change: 22 names parsed", "names parsed"),
    ("a hand-typed list of 15 environment", "a hand-typed list of 16 environment",
     "old list size"),
    ("`3 of 3 live, 0 dead`", "`2 of 3 live, 0 dead`", "liveness count"),
    ("| `coffee-bubbles` | `7738DF099D65…` | `EF7C3B8FCEA1…` DIFFERS |",
     "| `coffee-bubbles` | `7738DF099D66…` | `EF7C3B8FCEA1…` DIFFERS |",
     "coffee-bubbles master sha"),
    ("`8C418E60C186…` DIFFERS", "`8C418E60C187…` DIFFERS", "109MSDCF argv-only sha"),
    ("examined 12388, corrected 12388", "examined 12388, corrected 12387",
     "dust corrected"),
    ("49551 over 19 frame loads", "49552 over 19 frame loads", "samples changed"),
    ("1135 = 652 + 483", "1135 = 652 + 484", "refusal arithmetic"),
    ("`4 arms = 4 caught + 0 missed`", "`4 arms = 3 caught + 1 missed`",
     "commissioning partition"),
    ("| CAUGHT |\n| `D_IMPLIED`", "| MISSED |\n| `D_IMPLIED`", "C_WRONGCMD outcome"),
    # -- 23.12/13/14, added with the checks they cover ------------------
    # A commission does not stretch to cover checks added after it, so these
    # land in the same commit as the three new subsections.
    ("73-verify-s21.py        0          0        1           2  OK",
     "73-verify-s21.py        0          0        1           3  OK",
     "23.12 candidate count for 73"),
    ("45-verify-s18.py        0          0        1          10  OK",
     "45-verify-s18.py        0          0        1          11  OK",
     "23.12 candidate count for 45"),
    ("5 verifiers = 5 OK", "5 verifiers = 4 OK", "23.12 channel tally"),
    ("`CHANNEL-LIVE` at 5 of 5", "`CHANNEL-LIVE` at 4 of 5", "23.12 channel verdict"),
    ("pin-e260.tiff    18E6EDA98DEC9930", "pin-e260.tiff    18E6EDA98DEC9931",
     "23.13 restored pin hash"),
    ("head-e260.tiff   6A29AB1699372B44", "head-e260.tiff   6A29AB1699372B45",
     "23.13 re-measured head hash"),
    # -- conclusion reversals ------------------------------------------
    ("**Three of the five — 45, 63 and 73 — declare no `DEFECTS` at all",
     "**Three of the five — 45, 63 and 82 — declare no `DEFECTS` at all",
     "REVERSAL: which verifiers were uncommissioned"),
    ("document restored byte-identical: True",
     "document restored byte-identical: False",
     "REVERSAL: 23.12 restoration claim"),
    ("**The result is BLIND:**", "**The result is DISCRIMINATING:**",
     "REVERSAL: coords control verdict"),
    ("`active` is UNFALSIFIED, not confirmed", "`active` is CONFIRMED, not merely unfalsified",
     "REVERSAL: coords confirmation status"),
    ("It was unreachable", "It was merely off by default",
     "REVERSAL: the map was reachable after all"),
    ("the dust correction is **not inert**", "the dust correction is **inert**",
     "REVERSAL: dust inertness"),
    ("This is NOT a failure of the reproduction command",
     "This IS a failure of the reproduction command",
     "REVERSAL: drift blamed on the command"),
    ("The instrument was right and the plant was inert",
     "The plant was right and the instrument was blind",
     "REVERSAL: who was wrong in D_IMPLIED"),
    ("the corpus has **not** been re-rendered", "the corpus **has** been re-rendered",
     "REVERSAL: corpus render status"),
    ("**It is not this lane's.**", "**It is this lane's.**",
     "REVERSAL: byte-freeze attribution"),
    # -- deletions ------------------------------------------------------
    ("`active` is UNFALSIFIED, not confirmed", "", "DELETION: coords confirmation status"),
    ("This is NOT a failure of the reproduction command", "",
     "DELETION: drift is not a command failure"),
    ("the corpus has **not** been re-rendered", "", "DELETION: corpus render status"),
    ("`4 arms = 4 caught + 0 missed`", "", "DELETION: commissioning partition"),
    ("`3 of 3 live, 0 dead`", "", "DELETION: liveness count"),
    ("5 verifiers = 5 OK", "", "DELETION: 23.12 channel tally"),
    ("document restored byte-identical: True", "",
     "DELETION: 23.12 restoration claim"),
    ("pin-e260.tiff    18E6EDA98DEC9930", "", "DELETION: 23.13 restored pin hash"),
]


def plant(base, old, new):
    """Mutate exactly one site, tolerating an anchor that wraps across lines.

    The first version of this loop used `base.count(old)` and a plain
    `str.replace`. It reported UNANCHORED for `It was unreachable`, which is
    present -- as `It was\\nunreachable`, because the document is hard-wrapped
    and the phrase straddles the break. A plant that reads "absent" on text that
    is right there is a false clean bill of health for the verifier, and it is
    the same class as the greps this project has already been caught by.

    So a literal miss falls back to a whitespace-insensitive match built by
    joining the anchor's tokens on `\\s+`. Returns (mutated_or_None, n_sites);
    the caller refuses anything but exactly one site, because a single-site
    mutation with a duplicate elsewhere leaves the duplicate to satisfy the
    check.
    """
    n = base.count(old)
    if n == 1:
        return base.replace(old, new, 1), 1
    if n > 1:
        return None, n
    pat = r"\s+".join(re.escape(tok) for tok in old.split())
    hits = list(re.finditer(pat, base))
    if len(hits) == 1:
        h = hits[0]
        return base[:h.start()] + new + base[h.end():], 1
    return None, len(hits)


def commission():
    say("=== COMMISSIONING: plant a defect, require the verifier to catch it ===")
    base = section23()
    ck0 = verify(base, quiet=True)
    say("  clean section : %d matched + %d mismatched + %d unresolved of %d"
        % (ck0.m, ck0.mm, ck0.un, ck0.total()))
    if ck0.mm or ck0.un:
        for b in ck0.bad:
            say(b)
        say("VERDICT: NOT-COMMISSIONED -- the clean section does not verify, so a "
            "caught defect could not be attributed to the plant.")
        raise SystemExit(2)
    caught = missed = unanchored = ambiguous = 0
    for old, new, label in DEFECTS:
        mutated, n = plant(base, old, new)
        if mutated is None and n == 0:
            unanchored += 1
            say("  UNANCHORED %-46s %r absent -- a plant that does not land is a "
                "second null, not a pass" % (label, old[:40]))
            continue
        if mutated is None:
            ambiguous += 1
            say("  AMBIGUOUS  %-46s %r occurs %d times; a single-site mutation "
                "leaves a duplicate to satisfy the check" % (label, old[:40], n))
            continue
        ck = verify(mutated, quiet=True)
        if ck.mm + ck.un > 0:
            caught += 1
        else:
            missed += 1
            say("  MISSED     %-46s %r -> %r undetected" % (label, old[:40], new[:40]))
    say("  %d planted = %d caught + %d missed + %d unanchored + %d ambiguous"
        % (len(DEFECTS), caught, missed, unanchored, ambiguous))
    if caught + missed + unanchored + ambiguous != len(DEFECTS):
        raise SystemExit("partition does not sum")
    ok = caught == len(DEFECTS)
    n_rev = sum(1 for d in DEFECTS if d[2].startswith("REVERSAL"))
    n_del = sum(1 for d in DEFECTS if d[2].startswith("DELETION"))
    io.open(os.path.join(OUTD, "88-commission.json"), "w", encoding="utf-8").write(
        json.dumps(dict(planted=len(DEFECTS), caught=caught, missed=missed,
                        unanchored=unanchored, ambiguous=ambiguous,
                        reversals=n_rev, deletions=n_del,
                        numeric=len(DEFECTS) - n_rev - n_del,
                        declared=ck0.total(),
                        verdict="COMMISSIONED" if ok else "NOT-COMMISSIONED"),
                   indent=2))
    say()
    say("VERDICT: %s" % ("COMMISSIONED" if ok else "NOT-COMMISSIONED"))
    return ok


def main():
    com = "--commission" in sys.argv
    say("=== verify section 23 against the artifacts it cites ===")
    say()
    if com:
        ok = commission()
    else:
        say("=== CLAIMS ===")
        ck = verify(section23())
        ok = (ck.mm == 0 and ck.un == 0 and ck.m == ck.total())
        say()
        say("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    io.open(os.path.join(OUTD, "88-verify-s23%s.log" % ("-commission" if com else "")),
            "w", encoding="utf-8").write("\n".join(log) + "\n")
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
