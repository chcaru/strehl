"""M-PHASE0-ZFIELD -- prove check_note.py can fail.

A checker that has only returned GREEN is an untested instrument. This harness
plants one defect at a time in scratch copies, requires a RED exit, and requires
the named check to be among the failures.

TEXT changes only the note. DATA changes only a stored JSON output. BOTH makes
the note and JSON agree on the same wrong value, so only an independent
re-derivation can catch it.
"""

import copy
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
LANE = HERE.parent
ROOT = LANE.parent.parent
NOTE = ROOT / "docs" / "research" / "M-PHASE0-ZFIELD.md"
CENSUS = LANE / "out" / "z1-census.json"
VERDICT = LANE / "out" / "z5-verdict.json"
CONTROLS = LANE / "out" / "z2-controls.json"
CHECK = HERE / "check_note.py"

ORIG_NOTE = NOTE.read_text(encoding="utf-8").replace("\r\n", "\n")
BASE_CENSUS = json.loads(CENSUS.read_text(encoding="utf-8"))
BASE_VERDICT = json.loads(VERDICT.read_text(encoding="utf-8"))
BASE_CONTROLS = json.loads(CONTROLS.read_text(encoding="utf-8"))

SOURCES = {
    "note": NOTE,
    "census": CENSUS,
    "verdict": VERDICT,
    "controls": CONTROLS,
}
CASE_NAMES = {
    "note": "note.md",
    "census": "z1-census.json",
    "verdict": "z5-verdict.json",
    "controls": "z2-controls.json",
}


class PlantError(Exception):
    pass


def wrap_re(phrase):
    return re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))


def resolve_once(text, phrase, label):
    hits = list(wrap_re(phrase).finditer(text))
    if len(hits) != 1:
        raise PlantError(
            "plant %r wrapped anchor matched %d sites (need exactly 1); "
            "INERT PLANT" % (label, len(hits))
        )
    return hits[0]


def retoken(matched, old, new):
    old_tokens = old.split()
    new_tokens = new.split()
    if len(old_tokens) != len(new_tokens):
        raise PlantError("token count differs: %r vs %r" % (old, new))
    if matched.split() != old_tokens:
        raise PlantError("resolved text does not match anchor tokens: %r" % old)
    out, i = [], 0
    for part in re.split(r"(\s+)", matched):
        if part.strip() == "":
            out.append(part)
        else:
            out.append(new_tokens[i])
            i += 1
    if i != len(new_tokens):
        raise PlantError("replacement token accounting failed for %r" % old)
    return "".join(out)


def replace_wrapped(text, old, new, label):
    match = resolve_once(text, old, label)
    replacement = retoken(match.group(0), old, new)
    changed = text[:match.start()] + replacement + text[match.end():]
    if changed == text:
        raise PlantError("plant %r produced identical text; INERT PLANT" % label)
    return changed


def replace_line(text, old, new, label):
    anchor = old + "\n"
    hits = text.count(anchor)
    if hits != 1:
        raise PlantError(
            "plant %r full-line anchor matched %d sites (need exactly 1); "
            "INERT PLANT" % (label, hits)
        )
    if len(old.split()) != len(new.split()):
        raise PlantError("plant %r changed the table-row token count" % label)
    start = text.find(anchor)
    changed = text[:start] + new + "\n" + text[start + len(anchor):]
    if changed == text:
        raise PlantError("plant %r produced identical text; INERT PLANT" % label)
    return changed


def delete_line(text, line, label):
    anchor = line + "\n"
    hits = text.count(anchor)
    if hits != 1:
        raise PlantError(
            "plant %r deletion anchor matched %d sites (need exactly 1); "
            "INERT PLANT" % (label, hits)
        )
    start = text.find(anchor)
    changed = text[:start] + text[start + len(anchor):]
    if changed == text:
        raise PlantError("plant %r deleted nothing; INERT PLANT" % label)
    return changed


def changed_json(base, path, old, new, label):
    obj = copy.deepcopy(base)
    cur = obj
    for part in path[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            raise PlantError(
                "plant %r JSON anchor %r is missing; INERT PLANT"
                % (label, " / ".join(path))
            )
        cur = cur[part]
    leaf = path[-1]
    if not isinstance(cur, dict) or leaf not in cur:
        raise PlantError(
            "plant %r JSON anchor %r is missing; INERT PLANT"
            % (label, " / ".join(path))
        )
    if cur[leaf] != old:
        raise PlantError(
            "plant %r JSON anchor %r expected %r, found %r"
            % (label, " / ".join(path), old, cur[leaf])
        )
    if old == new:
        raise PlantError("plant %r JSON mutation is inert" % label)
    cur[leaf] = new
    return obj


def plant_verdict_flip():
    label = "headline and section-6 verdict flip"
    # Flips both declarations. Its sibling below flips only section 6, which is
    # the plant that was MISSED while `says` searched the whole document: the
    # headline's surviving copy satisfied the presence check on its own.
    text = replace_wrapped(
        ORIG_NOTE,
        "So the honest verdict is **SURVIVE, NOT ROBUST**, and the lane's "
        "most useful output is",
        "So the honest verdict is **KILL, NOT SURVIVE**, and the lane's "
        "most useful output is",
        label,
    )
    text = replace_wrapped(
        text,
        "**SURVIVE, NOT ROBUST.** At the shipping operator's noise level the "
        "median WINNABLE",
        "**KILL, NOT SURVIVE.** At the shipping operator's noise level the "
        "median WINNABLE",
        label,
    )
    return {"note": text}


def plant_verdict_flip_section6_only():
    label = "section-6 verdict flip, headline left intact"
    text = replace_wrapped(
        ORIG_NOTE,
        "**SURVIVE, NOT ROBUST.** At the shipping operator's noise level the "
        "median WINNABLE",
        "**KILL, NOT SURVIVE.** At the shipping operator's noise level the "
        "median WINNABLE",
        label,
    )
    return {"note": text}


def plant_last_digit():
    label = "shipping F last digit"
    old = (
        "| **6.83 (shipping operator)** | **14.02%** | **SURVIVE** | "
        "**10.12%** | **SURVIVE** |"
    )
    new = (
        "| **6.83 (shipping operator)** | **14.03%** | **SURVIVE** | "
        "**10.12%** | **SURVIVE** |"
    )
    return {"note": replace_line(ORIG_NOTE, old, new, label)}


def plant_delete_census_row():
    label = "delete 109MSDCF census row"
    line = (
        "| 109MSDCF | 22 | 0.599 | 1.06 | 99.6% | 0.409 | 98.3% | "
        "1.28% | 0.4% |"
    )
    return {"note": delete_line(ORIG_NOTE, line, label)}


def plant_kill_mechanism_flip():
    label = "invert EASY and LOST"
    return {
        "note": replace_wrapped(
            ORIG_NOTE,
            "The kill would be by **EASY saturation**, not by LOST saturation "
            "— median EASY is 92.1%",
            "The kill would be by **LOST saturation**, not by EASY saturation "
            "— median EASY is 92.1%",
            label,
        )
    }


def plant_noise_lag_swap():
    label = "swap x/y noise lags"
    return {
        "note": replace_wrapped(
            ORIG_NOTE,
            "the autocorrelation falls to 1/e at **8 px in x and 12 px in y** "
            "(d4 pixels),",
            "the autocorrelation falls to 1/e at **12 px in x and 8 px in y** "
            "(d4 pixels),",
            label,
        )
    }


def plant_f_sensitivity_data():
    label = "F6.83 half3 median data"
    return {
        "verdict": changed_json(
            BASE_VERDICT,
            ("f_sensitivity", "summary", "F6.83_half3.0", "median_winnable"),
            0.1012,
            0.1013,
            label,
        )
    }


def plant_controls_data():
    label = "controls failure count data"
    return {
        "controls": changed_json(
            BASE_CONTROLS,
            ("n_fail",),
            0,
            1,
            label,
        )
    }


# Non-vacuous: note and census both say 23, while the primary NPY has 22 frames.
# The expected DERIVED check must therefore consult the cube rather than agreement.
def plant_self_consistent_n_frames():
    label = "self-consistent 109 n_frames"
    old = (
        "| 109MSDCF | 22 | 0.599 | 1.06 | 99.6% | 0.409 | 98.3% | "
        "1.28% | 0.4% |"
    )
    new = (
        "| 109MSDCF | 23 | 0.599 | 1.06 | 99.6% | 0.409 | 98.3% | "
        "1.28% | 0.4% |"
    )
    return {
        "note": replace_line(ORIG_NOTE, old, new, label),
        "census": changed_json(
            BASE_CENSUS,
            ("stacks", "109MSDCF", "1", "n_frames"),
            22,
            23,
            label,
        ),
    }


PLANTS = [
    (
        "headline and section-6 verdict flip",
        "TEXT",
        "verdict is not robust (headline)",
        plant_verdict_flip,
    ),
    (
        "section-6 verdict flip, headline intact",
        "TEXT",
        "verdict is not robust (section 6)",
        plant_verdict_flip_section6_only,
    ),
    (
        "shipping F last digit",
        "TEXT",
        "F=6.83 WINNABLE @ 1.5",
        plant_last_digit,
    ),
    (
        "delete 109MSDCF census row",
        "TEXT",
        "census row 109MSDCF",
        plant_delete_census_row,
    ),
    (
        "invert EASY and LOST",
        "TEXT",
        "kill mechanism named",
        plant_kill_mechanism_flip,
    ),
    (
        "swap x/y noise lags",
        "TEXT",
        "noise 1/e lag x",
        plant_noise_lag_swap,
    ),
    (
        "F6.83 half3 median data",
        "DATA",
        "F=6.83 WINNABLE @ 3.0",
        plant_f_sensitivity_data,
    ),
    (
        "controls failure count data",
        "DATA",
        "all controls green",
        plant_controls_data,
    ),
    (
        "self-consistent 109 n_frames",
        "BOTH",
        "109MSDCF n_frames from npy",
        plant_self_consistent_n_frames,
    ),
]


def copy_case(directory):
    directory.mkdir()
    paths = {}
    for key, source in SOURCES.items():
        target = directory / CASE_NAMES[key]
        shutil.copyfile(source, target)
        paths[key] = target
    return paths


def write_note(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path, obj):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def apply_changes(paths, family, changes, label):
    keys = set(changes)
    if family == "TEXT" and keys != {"note"}:
        raise PlantError("plant %r violates its TEXT taxonomy" % label)
    if family == "DATA" and ("note" in keys or not keys):
        raise PlantError("plant %r violates its DATA taxonomy" % label)
    if family == "BOTH" and ("note" not in keys or len(keys) < 2):
        raise PlantError("plant %r violates its BOTH taxonomy" % label)
    for key, value in changes.items():
        if key not in paths:
            raise PlantError("plant %r names unknown artefact %r" % (label, key))
        if key == "note":
            if value == ORIG_NOTE:
                raise PlantError("plant %r left the note unchanged" % label)
            write_note(paths[key], value)
        else:
            base = {
                "census": BASE_CENSUS,
                "verdict": BASE_VERDICT,
                "controls": BASE_CONTROLS,
            }[key]
            if value == base:
                raise PlantError("plant %r left %s unchanged" % (label, key))
            write_json(paths[key], value)


def normalize(data):
    return data.decode("utf-8", "replace").replace("\r\n", "\n")


def run_checker(paths):
    env = dict(os.environ)
    env["NOTE_PATH"] = str(paths["note"])
    env["CENSUS_PATH"] = str(paths["census"])
    env["VERDICT_PATH"] = str(paths["verdict"])
    env["CONTROLS_PATH"] = str(paths["controls"])
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        env=env,
    )
    return proc.returncode, normalize(proc.stdout), normalize(proc.stderr)


def failure_names(output):
    names = []
    for line in output.splitlines():
        match = re.match(r"^\s*FAIL \[[^\]]+\] (.*?):(?:\s|$)", line)
        if match:
            names.append(match.group(1))
    return names


def is_green(output):
    return any(line.strip() == "GREEN" for line in output.splitlines())


def main():
    outcomes = {"CAUGHT": [], "MISSED": [], "ERROR": []}
    with tempfile.TemporaryDirectory(prefix="zfield-commission-") as scratch:
        scratch = pathlib.Path(scratch)
        null_paths = copy_case(scratch / "00-null")
        rc, out, err = run_checker(null_paths)
        if rc != 0 or not is_green(out) or failure_names(out):
            print("FATAL: null control is not GREEN on scratch copies.")
            print(out)
            if err:
                print(err)
            return 2
        print("null control GREEN (scratch copies)")

        for family in ("TEXT", "DATA", "BOTH"):
            print("")
            print("%s plants" % family)
            print("-" * 78)
            selected = [p for p in PLANTS if p[1] == family]
            for index, (label, _, expected, mutate) in enumerate(selected, 1):
                case = scratch / ("%s-%02d" % (family.lower(), index))
                try:
                    paths = copy_case(case)
                    changes = mutate()
                    apply_changes(paths, family, changes, label)
                    rc, out, err = run_checker(paths)
                    fired = failure_names(out)
                    if rc == 1 and expected in fired:
                        outcomes["CAUGHT"].append(label)
                        print("  CAUGHT   %-37s -> %s" % (label, expected))
                    elif rc in (0, 1):
                        outcomes["MISSED"].append(label)
                        if rc == 0:
                            why = "GREEN; no expected failure"
                        else:
                            why = "RED via %s" % (
                                ", ".join(fired) if fired else "<no FAIL lines>"
                            )
                        print("  MISSED   %-37s -> %s" % (label, why))
                    else:
                        outcomes["ERROR"].append(label)
                        print(
                            "  ERROR    %-37s -> checker exit %d"
                            % (label, rc)
                        )
                        if out:
                            print(out)
                        if err:
                            print(err)
                except Exception as exc:
                    outcomes["ERROR"].append(label)
                    print("  ERROR    %-37s -> %s" % (label, exc))

    total = len(PLANTS)
    accounted = sum(len(v) for v in outcomes.values())
    if accounted != total:
        raise AssertionError(
            "plant accounting does not sum: %d outcomes for %d plants"
            % (accounted, total)
        )
    commissioned = len(outcomes["CAUGHT"]) == total
    print("")
    print("=" * 78)
    print("VERDICT: %s" % ("COMMISSIONED" if commissioned else "NOT COMMISSIONED"))
    print(
        "SUMMARY: CAUGHT %d / MISSED %d / ERROR %d / total %d"
        % (
            len(outcomes["CAUGHT"]),
            len(outcomes["MISSED"]),
            len(outcomes["ERROR"]),
            total,
        )
    )
    return 0 if commissioned else 1


if __name__ == "__main__":
    raise SystemExit(main())
