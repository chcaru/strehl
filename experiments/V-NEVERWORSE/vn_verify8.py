"""Re-derive every load-bearing number in RESULT.md section 8 from its record.

Commissioning history, kept because it is the reason this file looks like it
does. The first version of this checker ran 23/23 GREEN and then caught only
5 of 13 planted defects. Two causes, both of which made it verify itself rather
than the report:

  1. Eight checks compared git / M111 against constants written in the CHECKER.
     Mutating the document could not fail them. Every value is now PARSED OUT OF
     THE DOCUMENT and the document's value is what gets tested.
  2. The presence window was +/-220 chars, wide enough that the neighbouring
     table row's identical `+0.174` satisfied a mutated cell. Table claims are
     now matched per ROW, on the exact cell.

Three-state: a crash is a REFUSAL (rc=2), never a FAIL (rc=1) and never a pass.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DOC = os.path.join(HERE, "RESULT.md")
MECH = r"C:\dev\strehl-out\V-NEVERWORSE\mech\mechtest.json"
ADM = r"C:\dev\strehl-out\V-NEVERWORSE\mech\admission.json"
M111 = os.path.join(ROOT, "docs", "research", "M111-waxy-blobs.md")
PIN = "9b05d0b7"

fails = []
refused = []
checked = 0


def _flat(s):
    return re.sub(r"\s+", " ", s)


def row(body, label, what):
    """Return the cells of the unique table row whose first cell is `label`."""
    global checked
    checked += 1
    hits = [ln for ln in body.splitlines()
            if ln.startswith("|") and _flat(ln.split("|")[1]).strip() == label]
    if len(hits) != 1:
        fails.append("%s: %d rows have first cell %r, need exactly 1"
                     % (what, len(hits), label))
        return None
    return [c.strip() for c in hits[0].strip("|").split("|")]


def cell(cells, i, value, what):
    """The i-th cell must contain `value`; nothing outside the cell counts."""
    global checked
    checked += 1
    if cells is None:
        return
    if i >= len(cells):
        fails.append("%s: row has %d cells, wanted index %d"
                     % (what, len(cells), i))
        return
    if value not in cells[i]:
        fails.append("%s: cell %d is %r, does not contain %r"
                     % (what, i, cells[i], value))


def grab(body, pat, what):
    """Parse a value OUT of the document. The document is the claim."""
    global checked
    checked += 1
    m = re.findall(pat, body)
    if len(m) != 1:
        fails.append("%s: pattern %r matched %d times, need 1"
                     % (what, pat, len(m)))
        return None
    return m[0]


def main():
    global checked
    doc = io.open(DOC, encoding="utf-8").read()
    i8 = doc.index("## 8. The mechanism")
    j8 = doc.index("\n## ", i8 + 1)
    s8 = doc[i8:j8]

    # ---- 8.3 correlations: cell-exact, against the harness output ----
    try:
        m = json.load(io.open(MECH, encoding="utf-8"))
    except Exception as e:
        refused.append("mechtest.json unreadable: %s" % e)
        m = None
    if m:
        r = row(s8, "excess vs mixedness `4p(1-p)`", "mix row")
        cell(r, 1, "%+.3f" % m["rho_mix"], "rho_mix")
        cell(r, 2, "%.2f" % m["p_mix"], "p_mix")
        r = row(s8, "excess vs raw averaged fraction", "raw row")
        cell(r, 1, "%+.3f" % m["rho_raw"], "rho_raw")
        cell(r, 2, "%.2f" % m["p_raw"], "p_raw")

        rows = m["rows"]
        got = grab(s8, r"26 examined = \*\*(\d+) measured", "partition measured")
        checked += 1
        if got is not None and int(got) != len(rows):
            fails.append("doc says %s measured, mechtest has %d"
                         % (got, len(rows)))
        checked += 1
        if len(rows) + 2 != 26:
            fails.append("partition does not sum: %d + 2 != 26" % len(rows))

        mx = max(rows, key=lambda k: rows[k]["mix"])
        ex = max(rows, key=lambda k: rows[k]["excess"])
        checked += 2
        if mx != "109MSDCF":
            fails.append("most-mixed subject is %s, doc names 109MSDCF" % mx)
        if ex != "bee-2-cpl":
            fails.append("worst-excess subject is %s, doc names bee-2-cpl" % ex)
        for subj in ("109MSDCF", "bee-2-cpl", "flat-on-ruler-cpl"):
            if subj not in rows:
                fails.append("%s absent from mechtest rows" % subj)
                continue
            r = row(s8, "`%s`" % subj, "%s row" % subj)
            cell(r, 1, "%.3f" % rows[subj]["mix"], "%s mixedness" % subj)
            cell(r, 2, "%.3f" % rows[subj]["excess"], "%s excess" % subj)

        order = sorted(rows, key=lambda k: rows[k]["excess"])
        big = [k for k in rows if rows[k]["frames"] == 299]
        lo = [k for k in big if order.index(k) < len(order) // 3]
        hi = [k for k in big if order.index(k) >= 2 * len(order) // 3]
        checked += 1
        if not (lo and hi):
            fails.append("299-frame stacks are NOT at both extremes: "
                         "low=%s high=%s" % (lo, hi))

    # ---- 8.1 the switch census, parsed from the doc then re-derived ----
    try:
        a = json.load(io.open(ADM, encoding="utf-8"))
        subs = a["subjects"] if isinstance(a, dict) and "subjects" in a else a
        unset = [k for k, v in subs.items()
                 if str(v.get("soft_gate", "")).strip() in ("", "(unset)")]
        claimed = grab(s8, r"\(unset\)` on \*\*(\d+) of (\d+)\*\*", "census claim")
        checked += 1
        if claimed is not None and (int(claimed[0]), int(claimed[1])) != \
                (len(unset), len(subs)):
            fails.append("doc claims %s of %s unset, record has %d of %d"
                         % (claimed[0], claimed[1], len(unset), len(subs)))
    except Exception as e:
        refused.append("admission.json unreadable: %s" % e)

    # ---- 8.1 source drift: NUMBERS COME FROM THE DOC, git is the oracle ----
    drift = grab(s8, r"`softgate\.rs` differs by \*\*(\d+) lines\*\*",
                 "softgate drift")
    pair = grab(s8, r"`merge\.rs` by (\d+) and `focus\.rs` by (\d+)",
                "drift pair")
    want = {}
    if drift is not None:
        want["softgate.rs"] = int(drift)
    if pair is not None:
        want["merge.rs"], want["focus.rs"] = int(pair[0]), int(pair[1])
    for fn, w in sorted(want.items()):
        checked += 1
        try:
            p = subprocess.run(
                ["git", "-C", ROOT, "diff", "--numstat", PIN, "HEAD", "--",
                 "crates/strehl-core/src/" + fn], capture_output=True)
            out = p.stdout.decode("utf-8", "replace").split()
            got = int(out[0]) + int(out[1]) if len(out) >= 2 else 0
            if got != w:
                fails.append("%s drift measures %d lines, doc says %d"
                             % (fn, got, w))
        except Exception as e:
            refused.append("git diff %s: %s" % (fn, e))

    # ---- 8.4 the M111 material: EXTRACT FROM THE DOC, require it in M111 ----
    try:
        m111 = _flat(io.open(M111, encoding="utf-8").read())

        quote = [ln.lstrip(">").strip() for ln in s8.splitlines()
                 if ln.startswith(">")]
        checked += 1
        if not quote:
            fails.append("section 8.4 carries no blockquote to verify")
        else:
            q = _flat(" ".join(quote))
            checked += 1
            if q not in m111:
                fails.append("the quoted M111 mechanism is NOT verbatim in "
                             "M111-waxy-blobs.md: %r" % q[:90])

        tol = grab(s8, r"FOCUS_NOISE_SD` = \*\*([\d.]+)\*\*", "tolerance")
        checked += 1
        if tol is not None and tol not in m111:
            fails.append("tolerance %s taken from the doc is not in M111" % tol)

        coll = grab(s8, r"Admission falls \*\*(\d+) to (\d+)\*\*",
                    "n_eff collapse")
        if coll is not None:
            hi_, lo_ = coll
            r = row(s8, "0.60 – 0.65", "n_eff top row")
            cell(r, 3, hi_, "n_eff high end matches its own table")
            r = row(s8, "above 20", "n_eff bottom row")
            cell(r, 3, lo_, "n_eff low end matches its own table")
    except Exception as e:
        refused.append("M111 unreadable: %s" % e)

    print("\n%d checks: %d passed, %d FAILED, %d REFUSED"
          % (checked, checked - len(fails) - len(refused), len(fails),
             len(refused)))
    for f in fails:
        print("  FAIL    " + f)
    for r_ in refused:
        print("  REFUSED " + r_)
    if refused:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    # A crash is a REFUSAL, never a FAIL and never a pass: rc=2 is reserved for
    # "this checker did not run", so an exception can never be read as a
    # measured negative.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: checker crashed; no claim in section 8 is checked")
        sys.exit(2)
