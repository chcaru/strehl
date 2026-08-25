"""Transcription guard for M111 report section 18 (halo claim audit).

Every number in section 18 and facts P46-P54 is asserted against its source JSON,
and each check is pinned to its own fact row rather than to the file, so a
duplicate of the same value elsewhere cannot satisfy it.

Sources (read-only):
  experiments/M87-occlusion/data/56-bmf.json
  experiments/M87-occlusion/data/22-plant-truth.json

Run:  python experiments/M111-waxy-blobs/halo_claim_guard.py
Exit: 0 all checks pass, 1 otherwise.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.environ.get("M111_HALO_DATA") or os.path.join(ROOT, "experiments", "M87-occlusion", "data")
REPORT = os.path.join(ROOT, "docs", "research", "M111-waxy-blobs.md")

bmf_all = json.load(io.open(os.path.join(DATA, "56-bmf.json"), encoding="utf-8"))
bmf = bmf_all["regions"]["DAMAGE"]
noop = bmf_all["regions"]["NOOP"]
plant = json.load(io.open(os.path.join(DATA, "22-plant-truth.json"), encoding="utf-8"))

rows = {}
for line in io.open(REPORT, encoding="utf-8").read().split("\n"):
    for tag in ("P46", "P47", "P48", "P49", "P50", "P51", "P52", "P53", "P54"):
        if line.startswith("* **%s " % tag) or line.startswith("* **%s." % tag):
            if tag in rows:
                sys.exit("FAIL: duplicate fact row %s" % tag)
            rows[tag] = line
missing = [t for t in ("P46", "P47", "P49", "P50", "P51", "P52", "P54") if t not in rows]
if missing:
    sys.exit("FAIL: fact rows absent from report: %s" % missing)


def find(node, *path):
    for key in path:
        node = node[key]
    return node


checks = []


def pin(tag, literal, source_value, note):
    """Assert `literal` appears in fact row `tag` and restates `source_value`."""
    checks.append((tag, literal, source_value, note))


occ = plant["occluding (KB=90, two depths)"]
ctl = plant["CONTROL non-occluding (KB=KF=40, one depth)"]

# --- P46: blur-matched fidelity -----------------------------------------
pin("P46", "5.108", bmf["blur_sigma"], "blur sigma matching coarse suppression")
pin("P46", "20.46%", 100.0 * bmf["blur_fine"], "blur fine-band retention")
pin("P46", "90.58%", 100.0 * bmf["fine"], "correction fine-band retention")
pin("P46", "4.428", bmf["BMF"], "BMF = fine / blur_fine")
pin("P46", "0.9145749511849404", bmf["blur_coarse"], "matched coarse, blur arm")
pin("P46", "0.9145749511806655", bmf["coarse"], "matched coarse, correction arm")

# --- P49: bar V3 --------------------------------------------------------
pin("P49", "0.905812", bmf["fine"], "FINE band ratio")
pin("P49", "0.914575", bmf["coarse"], "COARSE band ratio")
pin("P49", "9.42%", 100.0 * (1.0 - bmf["fine"]), "fine band destroyed")
pin("P49", "8.54%", 100.0 * (1.0 - bmf["coarse"]), "coarse band removed")

# --- P50/P51: the non-occluding control ---------------------------------
pin("P50", "1.000", ctl["local-d40"]["moved_frac"], "control moved fraction")
pin("P50", "0.394", occ["local-d40"]["moved_frac"], "occluding moved fraction")
pin("P50", "2.5", ctl["local-d40"]["moved_frac"] / occ["local-d40"]["moved_frac"],
    "aggression ratio, control over real")
pin("P51", "\u2212186.6%", -ctl["local-d10"]["iso_delta_pct"], "control ISO d10")
pin("P51", "\u2212142.0%", -ctl["local-d20"]["iso_delta_pct"], "control ISO d20")
pin("P51", "+63.9%", ctl["local-d40"]["iso_delta_pct"], "control ISO d40")
pin("P51", "+215.9%", ctl["local-d10"]["rmse_band_delta_pct"], "control RMSE d10")
pin("P51", "+354.4%", ctl["local-d20"]["rmse_band_delta_pct"], "control RMSE d20")
pin("P51", "+558.4%", ctl["local-d40"]["rmse_band_delta_pct"], "control RMSE d40")
pin("P51", "2.9\u00d7", ctl["local-d10"]["ISO"] / ctl["F0_ISO"], "control ISO worsening at d10")

# --- P54: the forbidden band, derived from the rule ---------------------
DELTA, NFRAMES = 40, 299
forbidden = 2 * DELTA - 1
pin("P54", "**79**", forbidden, "frames with |k - k_F| < 40")
pin("P54", "**220**", NFRAMES - forbidden, "complement, the proposed arm")
pin("P54", "2.8\u00d7", (NFRAMES - forbidden) / forbidden, "how much larger the proposed arm is")

fails = []
for tag, literal, value, note in checks:
    row = rows[tag]
    if literal not in row:
        fails.append("%s: literal %r absent from its own fact row (%s)" % (tag, literal, note))
        continue
    digits = literal.lstrip("*+\u2212-").rstrip("*%\u00d7")
    try:
        stated = float(digits)
    except ValueError:
        fails.append("%s: literal %r not numeric" % (tag, literal))
        continue
    if abs(value) < 1e-9:
        ok = abs(stated) < 1e-9
    else:
        ok = abs(abs(stated) - abs(value)) <= 0.5 * 10 ** -(len(digits.split(".")[1]) if "." in digits else 0)
    if not ok:
        fails.append("%s: report says %s, source says %.6f  (%s)" % (tag, literal, value, note))

# Bars are booleans, so check them structurally rather than as text.
bars = bmf_all.get("bars", {})
expect = {"V1": True, "V2": True, "V3": False, "V4": True}
if {k: bool(v) for k, v in bars.items()} != expect:
    fails.append("bars changed at source: %r, expected %r" % (bars, expect))
if "V1 true, V2 true, V3 false, V4 true" not in rows["P49"]:
    fails.append("P49: bar verdict string does not match source bars")
if not (noop["fine"] == 1.0 and noop["coarse"] == 1.0 and noop["changed_frac"] == 0.0):
    fails.append("NOOP null no longer exact: %r" % noop)
if abs(bmf["blur_coarse"] - bmf["coarse"]) > 1e-10:
    fails.append("coarse match no longer exact: delta %.3e" % abs(bmf["blur_coarse"] - bmf["coarse"]))
if abs(bmf["BMF"] - bmf["fine"] / bmf["blur_fine"]) > 1e-9:
    fails.append("BMF is not fine/blur_fine at source; P46's gloss is wrong")
for d in ("local-d10", "local-d20", "local-d40"):
    if abs(ctl[d]["moved_frac"] - 1.0) > 1e-12:
        fails.append("control moved_frac not 1.0 at %s: %r" % (d, ctl[d]["moved_frac"]))
if not (ctl["local-d10"]["iso_delta_pct"] < 0 < ctl["local-d40"]["iso_delta_pct"]):
    fails.append("control ISO dose-response is no longer non-monotone; P51 is void")

for f in fails:
    print("FAIL  " + f)
print("%s  %d/%d checks passed" % ("RED" if fails else "GREEN", len(checks) - len(fails), len(checks)))
sys.exit(1 if fails else 0)
