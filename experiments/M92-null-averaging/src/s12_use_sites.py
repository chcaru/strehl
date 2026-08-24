"""M92b S12 -- use-site classification and pricing of every MISMATCH.

S10 says a constant disagrees with EXIF. That is not yet a defect. A constant
can disagree and be *inert*, and the corpus has three distinct innocent shapes:

  OPERATOR   -- passed to `focus_fields(cube, g, rn_e)`, which is the frozen
                detail operator. Rule 15 freezes the operator's constants so
                results compare across milestones; changing them to match EXIF
                would break comparability and is NOT the fix.
  PLANT      -- passed to `add_sensor_noise` over a SYNTHETIC image. The
                constant defines the plant; there is no truth to disagree with.
  SENSOR     -- passed to `gain_dn_per_e` / `read_noise_e` / `noise_var_dn`
                or used in `g*S + (rn*g)^2` over REAL stack pixels. Here the
                constant claims to describe the sensor, and EXIF can refute it.

Only SENSOR uses can carry the M92 defect. This script decides which is which
mechanically -- by walking the AST for the call sites each constant flows
into -- rather than by reading and asserting, and then prices the SENSOR ones
as the ratio of modelled single-frame sigma (wrong constant vs EXIF-correct
constant) at the stack's own measured median level.

Run:
  python experiments/M92-null-averaging/src/s12_use_sites.py
"""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import m57lib as M57  # noqa: E402
import s10_const_scan as S10  # noqa: E402

# Callee name -> role. Matched on the attribute/function name only, so
# `L1.focus_fields`, `K.L1.focus_fields` and `focus_fields` all hit.
OPERATOR_CALLS = {"focus_fields"}
PLANT_CALLS = {"add_sensor_noise", "add_noise", "synth_noise"}
SENSOR_CALLS = {"gain_dn_per_e", "read_noise_e", "noise_var_dn",
                "merged_sigma", "sigma_dn", "predicted_sigma"}


def callee_name(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def use_sites(tree, const_name):
    """Every call whose arguments mention `const_name`, plus bare-arithmetic
    uses (the `g*S + (rn*g)**2` shape, which is a sensor model written out
    longhand and reaches no named callee)."""
    calls, arith = [], 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for a in list(node.args) + [k.value for k in node.keywords]:
                if any(isinstance(n, ast.Name) and n.id == const_name
                       for n in ast.walk(a)):
                    nm = callee_name(node)
                    if nm:
                        calls.append(nm)
                    break
        elif isinstance(node, ast.BinOp):
            if any(isinstance(n, ast.Name) and n.id == const_name
                   for n in ast.walk(node)):
                arith += 1
    return calls, arith


def role_of(calls, arith):
    c = set(calls)
    roles = []
    if c & SENSOR_CALLS:
        roles.append("SENSOR")
    if arith and not (c & SENSOR_CALLS):
        # Longhand `g*S + (rn*g)**2` reaches no named callee. This must be
        # added even when the same name ALSO reaches the frozen operator --
        # that dual role is the finding, and suppressing it here would hide
        # exactly the instances that cannot be corrected in place.
        roles.append("SENSOR?")
    if c & OPERATOR_CALLS:
        roles.append("OPERATOR")
    if c & PLANT_CALLS:
        roles.append("PLANT")
    return roles or ["INERT"]


def sigma_dn(level_dn, g, rn_e):
    return (g * max(level_dn, 0.0) + (rn_e * g) ** 2) ** 0.5


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    by_name, _ = S10.load_truth()
    scan = json.load(open(os.path.join(M92.OUT, "s10_const_scan.json")))
    rows = [r for r in (scan["rows"] if isinstance(scan, dict) else scan)
            if r["verdict"] == "MISMATCH" and r["kind"] == "per-stack"]

    log("=" * 78)
    log("M92b S12 -- use-site classification of every per-stack MISMATCH")
    log("=" * 78)
    log("  OPERATOR = frozen detail operator (rule 15), EXIF does not apply")
    log("  PLANT    = defines a synthetic plant, no truth to disagree with")
    log("  SENSOR   = claims to describe the sensor -> EXIF can refute it")
    log("  LEVEL_DN = 250 DN above black, the regime M57's nulls were run in")
    log("")

    LEVEL = 250.0
    out = []
    for r in sorted(rows, key=lambda r: (r["file"], r["line"])):
        p = os.path.join(S10.REPO, r["file"].replace("/", os.sep))
        try:
            tree = ast.parse(open(p, encoding="utf-8",
                                  errors="replace").read())
        except (OSError, SyntaxError):
            continue
        calls, arith = use_sites(tree, r["name"])
        roles = role_of(calls, arith)

        # price it: worst stack in the file, sigma ratio at LEVEL
        worst, ratio = None, 1.0
        for s in r["stacks"]:
            iso = by_name[s]["iso"]
            gt_g, gt_rn = M57.gain_dn_per_e(iso), M57.read_noise_e(iso)
            if r["name"] in ("ISO", "iso", "ISO_"):
                bad_g = M57.gain_dn_per_e(r["value"])
                bad_rn = M57.read_noise_e(r["value"])
            elif r["name"] in ("G", "GAIN", "GAIN_DN_PER_E", "g_dn"):
                bad_g, bad_rn = r["value"], gt_rn
            else:
                bad_g, bad_rn = gt_g, r["value"]
            rr = sigma_dn(LEVEL, bad_g, bad_rn) / sigma_dn(LEVEL, gt_g, gt_rn)
            if abs(rr - 1.0) > abs(ratio - 1.0):
                worst, ratio = s, rr
        rec = dict(file=r["file"], line=r["line"], name=r["name"],
                   value=r["value"], stacks=r["stacks"], roles=roles,
                   calls=sorted(set(calls)), arith=arith,
                   worst_stack=worst, sigma_ratio=ratio)
        out.append(rec)

    for want in ("SENSOR", "SENSOR?", "OPERATOR", "PLANT", "INERT"):
        sel = [r for r in out if r["roles"][0] == want]
        if not sel:
            continue
        log("-" * 78)
        log(f"  role {want}: {len(sel)} instance(s)")
        log("-" * 78)
        for r in sel:
            extra = ("+" + ",".join(r["roles"][1:])) if len(r["roles"]) > 1 \
                else ""
            log(f"  {r['file']}:{r['line']}  {r['name']} = {r['value']:g}"
                f"  {extra}")
            log(f"      calls: {','.join(r['calls']) or '-'}"
                f"   binops: {r['arith']}")
            log(f"      worst stack {r['worst_stack']}: modelled sigma is"
                f" {r['sigma_ratio']:.4f}x the EXIF-correct value at"
                f" {LEVEL:g} DN")
        log("")

    log("=" * 78)
    n_sensor = sum(1 for r in out if "SENSOR" in r["roles"] or "SENSOR?" in r["roles"])
    n_op = sum(1 for r in out if "OPERATOR" in r["roles"])
    both = [r for r in out
            if ("SENSOR" in r["roles"] or "SENSOR?" in r["roles"])
            and "OPERATOR" in r["roles"]]
    log(f"  {len(out)} MISMATCHes: {n_sensor} reach a sensor model,"
        f" {n_op} reach the frozen operator.")
    log(f"  {len(both)} instance(s) reach BOTH from the SAME assignment --")
    log("  one variable serving the frozen operator and the sensor model at")
    log("  once. Those cannot be corrected in place: fixing the sensor use")
    log("  silently unfreezes the operator and breaks cross-milestone")
    log("  comparability (rule 15).")
    for r in both:
        log(f"      {r['file']}:{r['line']}  {r['name']} = {r['value']:g}"
            f"   sigma x{r['sigma_ratio']:.4f} on {r['worst_stack']}")

    with open(os.path.join(M92.OUT, "s12_use_sites.json"), "w",
              encoding="utf-8") as fh:
        json.dump(dict(level_dn=LEVEL, rows=out), fh, indent=1)
    with open(os.path.join(M92.OUT, "s12_use_sites.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote out/s12_use_sites.{json,log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
