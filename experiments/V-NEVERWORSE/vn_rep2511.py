"""Tables and inline values for section 9.25.11, generated from the records.

Same contract as `vn_rep25.py`: nothing in the retraction is typed by hand, and
every inline value is anchored on a neighbouring literal so that a presence
check cannot be satisfied by a duplicate of the number elsewhere in the file.

Records read:
  shipfr-pin-9b05d0b7.json   the pinned binary, --limit 44/45/46/47.
      NOT `shipfr.json`. Section 9.25.11 reports the measurement made on pin
      44C2F2CD2E5B2894, and 9.26 re-ran the same script against a newer
      binary, overwriting `shipfr.json` in place. A section must read the
      record it was actually generated from, not a filename a later run can
      take over -- `vn_verify2511` went RED the moment that happened, which is
      how this was found.
  regout.json   the neighbour-relative registration screen
  shipped46.json  the band-swap commissioning of the model arms
  pfvar.json    the per-frame variance arm that returned UNDECIDED
"""
import io
import json
import os
import sys

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
SHIPFR_9_25_11 = "shipfr-pin-9b05d0b7.json"
GB = r"C:\dev\strehl-out\V-NEVERWORSE\gbundle"


def rec(name, where=OUT):
    p = os.path.join(where, name)
    if not os.path.exists(p):
        raise SystemExit("REFUSED: no record at %s" % p)
    return json.load(io.open(p, encoding="utf-8"))


def tables():
    sf, ro, sh = rec(SHIPFR_9_25_11), rec("regout.json"), rec("shipped46.json")
    t = {}

    rows = ["| frames stacked | one frame added | kind | L3 | L4 | L5 | L6 |",
            "|---|---|---|---:|---:|---:|---:|"]
    for s in sf["steps"]:
        r = s["ratio"]
        kind = "**the accused**" if s["kind"] == "ROGUE" else "null"
        rows.append("| %d -> %d | `%s` | %s | %.3f | %.3f | %.3f | %.3f |"
                    % (s["frm"], s["to"],
                       "DSC%05d.ARW" % (s["to"]), kind,
                       r[3], r[4], r[5], r[6]))
    t["shipfr"] = "\n".join(rows)

    meta = json.load(io.open(os.path.join(GB, "bee-2-cpl.json"),
                             encoding="utf-8"))
    by = {int(r["frame"]): r for r in meta["rows"]}
    rows = ["| source frame | state | `ncc_b` | fitted scale |",
            "|---|---|---:|---:|"]
    for k in (44, 45, 46, 47, 48):
        r = by[k]
        mark = "**" if k == ro["rogue"] else ""
        rows.append("| %s%d%s | %s%s%s | %s%.4f%s | %s%.4f%s |"
                    % (mark, k, mark, mark, r["state"], mark,
                       mark, r["ncc_b"], mark, mark, r["scale"], mark))
    t["reg46"] = "\n".join(rows)

    rows = ["| quantity | value |", "|---|---:|",
            "| frame %d `ncc_b` | %.4f |" % (ro["rogue"], ro["rogue_ncc"]),
            "| median `ncc_b` of its neighbours | %.4f |"
            % ro["rogue_neighbour_median"],
            "| its deviation from them | **%.4f** |" % ro["rogue_deviation"],
            "| next worst deviation in the stack | %.4f |" % ro["next_worst"],
            "| frames screened / frames in stack | %d / %d |"
            % (ro["n_screened"], ro["n_total"]),
            "| POOR-REG frames flagged | %d of %d |"
            % (ro["n_poor_flagged"], ro["n_poor_reg"]),
            "| frames flagged in the whole stack | %s |"
            % ", ".join(str(x) for x in ro["flagged"])]
    t["regout"] = "\n".join(rows)
    _ = sh
    return t


def values():
    sf, ro = rec(SHIPFR_9_25_11), rec("regout.json")
    sh, pf = rec("shipped46.json"), rec("pfvar.json")
    c = sh["commission"]
    l5 = [x for x in sf["steps"] if x["kind"] == "ROGUE"][0]["ratio"][5]
    margin = abs(ro["next_worst"]) and \
        abs(ro["rogue_deviation"] / ro["next_worst"])
    ship_l5 = [r for r in pf["rows"] if r["band"] == 5][0]["rogue_shared"]
    return {
        "shipfr_rogue": "**%.3fx**" % l5,
        "shipfr_null": "**%.3fx**" % sf["worst_null"],
        "g1": "%.3g" % c["g1_gain_drift"],
        "regdev": "| its deviation from them | **%.4f** |"
                  % ro["rogue_deviation"],
        "regnext": "just %.4f" % ro["next_worst"],
        "regmargin": "a %.0fx margin" % margin,
        "regpoor": "**%d of the %d POOR-REG frames**"
                   % (ro["n_poor_flagged"], ro["n_poor_reg"]),
        "suff": "**%.2fx of the %.2fx**" % (c["g4_sufficiency"], c["g2_plant"]),
        "nec": "only %.2fx" % c["g5_necessity"],
        "varratio": "**%.2fx**" % pf["var_rogue_over_median"],
        "ordmove": "**%.0fx**" % pf["ordinary_move"],
        "shipl5": "**%.5f**" % ship_l5,
        "ent": "entitlement of %.5f" % pf["entitlement"],
    }


if __name__ == "__main__":
    t, v = tables(), values()
    for k, s in t.items():
        print("=== TABLE %s ===\n%s\n" % (k, s))
    for k, s in v.items():
        print("VALUE %-14s %s" % (k, s))
    sys.exit(0)
