#!/usr/bin/env python3
"""Independent, mutation-commissioned verifier for the M150 capture request."""
from __future__ import annotations
import argparse
import hashlib
import math
import re
import tempfile
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAPTURE = ROOT / "docs/capture-requests/2026-09-319-frame-session.md"
PROPOSAL = ROOT / "docs/proposals/2026-09-truth-referenced-detail.md"
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
OWNER_ACTIONS = ROOT / "docs/OWNER-ACTIONS.md"

@dataclass(frozen=True)
class Result:
    check_id: str
    defect_class: str
    passed: bool
    evidence: str

def emit(value: object = "") -> None:
    print(str(value).encode("ascii", "replace").decode("ascii"))

def norm(text: str) -> str:
    replacements = {
        "\u00d7": "x", "\u2192": "->", "\u2010": "-", "\u2011": "-",
        "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " ",
    }
    text = unicodedata.normalize("NFC", text)
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()

def clean_cell(cell: str) -> str:
    return norm(cell.replace("**", "").replace("`", "").strip())

def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")

def unique_line_index(lines: list[str], predicate, description: str) -> int:
    hits = [i for i, line in enumerate(lines) if predicate(line)]
    if len(hits) != 1:
        raise ValueError(f"{description}: expected one line, found {len(hits)}")
    return hits[0]

def markdown_table_after(lines: list[str], start_index: int, header_prefix: str) -> list[tuple[str, str, str]]:
    header = unique_line_index(lines[start_index:], lambda line: line.strip().startswith(header_prefix), f"table header {header_prefix!r}") + start_index
    rows: list[tuple[str, str, str]] = []
    for line in lines[header + 2:]:
        if not line.strip().startswith("|"):
            break
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        cells += [""] * (3 - len(cells))
        rows.append((cells[0], cells[1], " | ".join(cells[2:])))
    return rows

def integer_cell(cell: str) -> int | None:
    cleaned = clean_cell(cell).replace(",", "")
    return int(cleaned) if re.fullmatch(r"\d+", cleaned) else None

def row_map(rows: list[tuple[str, str, str]]) -> tuple[dict[str, tuple[int | None, str]], list[str]]:
    mapped: dict[str, tuple[int | None, str]] = {}
    duplicates: list[str] = []
    for raw_label, raw_count, purpose in rows:
        label = clean_cell(raw_label)
        if label in mapped:
            duplicates.append(label)
        mapped[label] = (integer_cell(raw_count), purpose.strip())
    return mapped, duplicates

def add(results: list[Result], check_id: str, defect_class: str, passed: bool, evidence: str) -> None:
    results.append(Result(check_id, defect_class, bool(passed), evidence))

def sum_labels(mapping: dict[str, tuple[int | None, str]], labels: list[str]) -> int | None:
    values = [mapping.get(label, (None, ""))[0] for label in labels]
    return None if any(value is None for value in values) else sum(int(value) for value in values)

def only_allowed_number_occurrences(text: str, token: str, fragments: list[str]) -> tuple[bool, str]:
    haystack = norm(text).lower()
    pattern = rf"(?<!\d){re.escape(token)}(?!\d)"
    actual = {m.start() for m in re.finditer(pattern, haystack)}
    allowed: set[int] = set()
    missing = 0
    for raw_fragment in fragments:
        fragment = norm(raw_fragment).lower()
        starts = [m.start() for m in re.finditer(re.escape(fragment), haystack)]
        if len(starts) != 1:
            missing += 1
            continue
        allowed.update(starts[0] + m.start() for m in re.finditer(pattern, fragment))
    return not missing and actual == allowed, f"actual={len(actual)} allowed={len(allowed)} missing_fragments={missing}"

def resolve_reference(raw_path: str) -> tuple[Path | None, bool, int]:
    literal = ROOT / raw_path
    if literal.is_file():
        return literal, True, 1
    matches = list(ROOT.rglob(Path(raw_path).name))
    return (matches[0], False, 1) if len(matches) == 1 else (None, False, len(matches))

PHYSICAL = OrderedDict([
    ("reset pre-flight P0", 6), ("reset pre-flight P1", 6),
    ("start S4-A", 6), ("sw4-A", 55), ("end E4-A", 6),
    ("start S4-B", 6), ("sw4-B", 55), ("end E4-B", 6),
    ("start S10-A", 6), ("sw10-A", 27), ("end E10-A", 6),
    ("start S10-B", 6), ("sw10-B", 27), ("end E10-B", 6),
    ("sw1 checker-only", 91),
    ("TR-REF-NEAR", 32), ("TR-REF-MID", 32), ("TR-REF-FAR", 32),
    ("flats A", 32), ("flats B", 32), ("darks A", 32), ("darks B", 32),
    ("TC0-P0", 6), ("TC0-P1", 6),
    ("TC0-S4-A", 6), ("TC0-sw4-A", 55), ("TC0-E4-A", 6),
    ("TC0-S4-B", 6), ("TC0-sw4-B", 55), ("TC0-E4-B", 6),
    ("TC0-S10-A", 6), ("TC0-sw10-A", 27), ("TC0-E10-A", 6),
    ("TC0-S10-B", 6), ("TC0-sw10-B", 27), ("TC0-E10-B", 6),
    ("TC0-FLAT-A", 32), ("TC0-FLAT-B", 32), ("TC0-DARK-A", 32), ("TC0-DARK-B", 32),
])
SUMMARY = OrderedDict([
    ("existing claim/calibration", 383), ("existing fixed-focus witnesses", 60),
    ("reference subject", 96), ("TC0 scored focus", 164),
    ("TC0 fixed-focus witnesses", 60), ("TC0 calibration", 128),
    ("replacement inverted M1 block", 448), ("scored session total T_session", 891),
])
CONVERTER_FOCUS = ["sw4-A", "sw4-B", "sw10-A", "sw10-B", "sw1 checker-only"]
CONVERTER_CAL = ["flats A", "flats B", "darks A", "darks B"]
CONVERTER_WITNESSES = ["reset pre-flight P0", "reset pre-flight P1", "start S4-A", "end E4-A", "start S4-B", "end E4-B", "start S10-A", "end E10-A", "start S10-B", "end E10-B"]
REFERENCE = ["TR-REF-NEAR", "TR-REF-MID", "TR-REF-FAR"]
TC0_FOCUS = ["TC0-sw4-A", "TC0-sw4-B", "TC0-sw10-A", "TC0-sw10-B"]
TC0_WITNESSES = ["TC0-P0", "TC0-P1", "TC0-S4-A", "TC0-E4-A", "TC0-S4-B", "TC0-E4-B", "TC0-S10-A", "TC0-E10-A", "TC0-S10-B", "TC0-E10-B"]
TC0_CAL = ["TC0-FLAT-A", "TC0-FLAT-B", "TC0-DARK-A", "TC0-DARK-B"]
BRACKETS = CONVERTER_FOCUS + TC0_FOCUS
ADDED_PROPOSAL = OrderedDict((name, PHYSICAL[name]) for name in REFERENCE + TC0_WITNESSES + TC0_FOCUS + TC0_CAL)
KNOWN_IDS = {
    "P0", "P1", "S4-A", "S4-B", "E4-A", "E4-B", "S10-A", "S10-B", "E10-A", "E10-B",
    "sw1", "sw4", "sw10", "sw4-A", "sw4-B", "sw10-A", "sw10-B", "TR-REF-NEAR", "TR-REF-MID", "TR-REF-FAR",
    "TC0-P0", "TC0-P1", "TC0-S4-A", "TC0-S4-B", "TC0-E4-A", "TC0-E4-B",
    "TC0-S10-A", "TC0-S10-B", "TC0-E10-A", "TC0-E10-B", "TC0-sw4-A", "TC0-sw4-B",
    "TC0-sw10-A", "TC0-sw10-B", "TC0-FLAT-A", "TC0-FLAT-B", "TC0-DARK-A", "TC0-DARK-B",
}
def verify(capture_path: Path) -> tuple[list[Result], dict[str, object]]:
    results: list[Result] = []
    raw = capture_path.read_bytes()
    capture = raw.decode("utf-8")
    lines = capture.splitlines()
    flat = norm(capture)
    flow = norm(re.sub(r"(?m)^\s*>\s?", "", capture))
    lower, flow_lower = flat.lower(), flow.lower()
    facts: dict[str, object] = {"sha256": hashlib.sha256(raw).hexdigest(), "capture_lines": len(lines)}

    # Independent ground truth.
    proposal = read_utf8(PROPOSAL)
    proposal_lines = proposal.splitlines()
    try:
        anchor = unique_line_index(proposal_lines, lambda line: "Add the following" in line and "448 frames" in line, "proposal 448 anchor")
        rows = markdown_table_after(proposal_lines, anchor, "| Block | Frames")
        pmap, dupes = row_map(rows)
        actual = {name: pmap.get(name, (None, ""))[0] for name in ADDED_PROPOSAL}
        add(results, "truth.proposal-table-unique", "ground-truth", not dupes, f"duplicates={dupes}")
        add(results, "truth.proposal-physical-rows", "ground-truth", actual == dict(ADDED_PROPOSAL), f"rows={len(actual)}")
        p_ref = sum(actual[name] or 0 for name in REFERENCE)
        p_focus = sum(actual[name] or 0 for name in TC0_FOCUS)
        p_witness = sum(actual[name] or 0 for name in TC0_WITNESSES)
        p_cal = sum(actual[name] or 0 for name in TC0_CAL)
        add(results, "truth.proposal-reference", "ground-truth", p_ref == 96, f"3x32={p_ref}")
        add(results, "truth.proposal-focus", "ground-truth", p_focus == 164, f"55+55+27+27={p_focus}")
        add(results, "truth.proposal-witness", "ground-truth", p_witness == 60, f"10x6={p_witness}")
        add(results, "truth.proposal-calibration", "ground-truth", p_cal == 128, f"4x32={p_cal}")
        p_sum = sum(value or 0 for value in actual.values())
        add(results, "truth.proposal-total", "ground-truth", p_sum == p_ref + p_focus + p_witness + p_cal == 448, f"sum={p_sum}")
        derivation = re.search(r"Replace that (\d+)-frame block with this (\d+)-frame block: the live (\d+)-frame request grows by (\d+) to \*\*(\d+)\*\*", norm(proposal))
        d_ok, d_ev = False, "not parsed"
        if derivation:
            old_block, new_block, old_total, growth, new_total = map(int, derivation.groups())
            computed = old_total - old_block + new_block
            d_ok = (old_block, new_block, old_total, growth, new_total, computed) == (160, 448, 603, 288, 891, 891)
            d_ev = f"{old_total}-{old_block}+{new_block}={computed}; growth={growth}; stated={new_total}"
        add(results, "truth.proposal-replacement", "ground-truth", d_ok, d_ev)
    except Exception as exc:
        add(results, "truth.proposal-parse", "ground-truth", False, repr(exc))

    score_lines = read_utf8(SCORECARD).splitlines()
    expected_holdout = norm(
        "The holdout unit is **subject plus uninterrupted capture session**, not a directory or step width. "
        "Rendering, tuning, or reading an outcome on any member burns every member of that unit. A `HOLDOUT` "
        "capture may be decoded to build the frozen common input and input-only site manifest, but no output, "
        "metric, visual verdict, parameter sweep, or code-acceptance decision may be seen before the registered score run."
    )
    actual_holdout = norm(" ".join(score_lines[344:349])) if len(score_lines) >= 349 else ""
    add(results, "truth.holdout-lines-345-349", "ground-truth", actual_holdout == expected_holdout, f"source_lines={len(score_lines)}")

    owner = read_utf8(OWNER_ACTIONS)
    owner_lines = owner.splitlines()
    try:
        owner_heading = unique_line_index(owner_lines, lambda line: "The capture ask is now" in line and "two sittings, not one" in line, "owner heading")
        sitting_rows = markdown_table_after(owner_lines, owner_heading, "| sitting | frames")
        sitting_counts = [integer_cell(row[1]) for row in sitting_rows]
        add(results, "truth.owner-sitting-counts", "ground-truth", sitting_counts == [768, 891, 1659], f"counts={sitting_counts}")
        add(results, "truth.owner-sitting-sum", "ground-truth", sitting_counts[:2] == [768, 891] and sum(sitting_counts[:2]) == sitting_counts[2], "768+891=1659")
        rehearsal_anchor = unique_line_index(owner_lines, lambda line: "rehearsal's 768 frames" in line, "owner rehearsal")
        rehearsal_rows = markdown_table_after(owner_lines, rehearsal_anchor, "| block | frames")
        rehearsal_counts = [integer_cell(row[1]) for row in rehearsal_rows]
        expected_rehearsal = [164, 60, 128, 96, 128, 96, 96, 768]
        add(results, "truth.owner-rehearsal-blocks", "ground-truth", rehearsal_counts == expected_rehearsal, f"counts={rehearsal_counts}")
        add(results, "truth.owner-rehearsal-sum", "ground-truth", sum(x or 0 for x in rehearsal_counts[:-1]) == rehearsal_counts[-1] == 768, f"sum={sum(x or 0 for x in rehearsal_counts[:-1])}")
        add(results, "truth.owner-ask2a-excluded", "ground-truth", "plus the two frames of Ask 2a" in owner, "Ask 2a stated separately")
    except Exception as exc:
        add(results, "truth.owner-parse", "ground-truth", False, repr(exc))

    # Target block table and independently derived arithmetic.
    mapping: dict[str, tuple[int | None, str]] = {}
    physical_labels: list[str] = []
    try:
        frame_heading = unique_line_index(lines, lambda line: line.startswith("## Frame counts"), "capture frame heading")
        rows = markdown_table_after(lines, frame_heading, "| Block | Frames")
        mapping, duplicates = row_map(rows)
        labels = [clean_cell(row[0]) for row in rows]
        physical_labels = [label for label in labels if label not in SUMMARY]
        summary_labels = [label for label in labels if label in SUMMARY]
        add(results, "arith.table-parsed", "arithmetic", len(rows) == 48, f"rows={len(rows)}")
        add(results, "arith.no-duplicate-rows", "arithmetic", not duplicates, f"duplicates={duplicates}")
        add(results, "arith.physical-row-order", "arithmetic", physical_labels == list(PHYSICAL), f"physical_rows={len(physical_labels)}")
        add(results, "arith.summary-row-order", "arithmetic", summary_labels == list(SUMMARY), f"summary_rows={len(summary_labels)}")
        for label, expected in PHYSICAL.items():
            actual = mapping.get(label, (None, ""))[0]
            add(results, f"arith.physical.{label}", "arithmetic", actual == expected, f"actual={actual} expected={expected}")
        add(results, "internal.all-block-purposes-present", "internal-consistency", all(mapping.get(label, (None, ""))[1].strip() for label in PHYSICAL), "all 40 physical rows have purposes")
        physical_sum = sum_labels(mapping, list(PHYSICAL))
        facts["physical_sum"] = physical_sum
        add(results, "arith.physical-sum", "arithmetic", physical_sum == 891, f"sum={physical_sum}")
        derived = {
            "existing claim/calibration": sum_labels(mapping, CONVERTER_FOCUS + CONVERTER_CAL),
            "existing fixed-focus witnesses": sum_labels(mapping, CONVERTER_WITNESSES),
            "reference subject": sum_labels(mapping, REFERENCE),
            "TC0 scored focus": sum_labels(mapping, TC0_FOCUS),
            "TC0 fixed-focus witnesses": sum_labels(mapping, TC0_WITNESSES),
            "TC0 calibration": sum_labels(mapping, TC0_CAL),
        }
        facts["derived_groups"] = derived
        for label, expected in list(SUMMARY.items())[:6]:
            stated, value = mapping.get(label, (None, ""))[0], derived[label]
            add(results, f"arith.group.{label}", "arithmetic", value == expected == stated, f"derived={value} stated={stated} expected={expected}")
        replacement = sum((derived[name] or 0) for name in ["reference subject", "TC0 scored focus", "TC0 fixed-focus witnesses", "TC0 calibration"])
        replacement_stated = mapping.get("replacement inverted M1 block", (None, ""))[0]
        add(results, "arith.replacement-448", "arithmetic", replacement == replacement_stated == 448, f"96+164+60+128={replacement}; stated={replacement_stated}")
        total_groups = sum((derived[name] or 0) for name in derived)
        total_stated = mapping.get("scored session total T_session", (None, ""))[0]
        facts["stated_total"] = total_stated
        add(results, "arith.stated-total", "arithmetic", total_groups == physical_sum == total_stated == 891, f"groups={total_groups} rows={physical_sum} stated={total_stated}")
        replacement_terms = [int(x) for x in re.findall(r"\d+", mapping.get("replacement inverted M1 block", (None, ""))[1])]
        total_terms = [int(x) for x in re.findall(r"\d+", mapping.get("scored session total T_session", (None, ""))[1])]
        add(results, "arith.replacement-expression", "arithmetic", replacement_terms == [96, 164, 60, 128] and sum(replacement_terms) == replacement_stated, f"terms={replacement_terms}")
        add(results, "arith.total-expression", "arithmetic", total_terms == [383, 60, 96, 164, 60, 128] and sum(total_terms) == total_stated, f"terms={total_terms}")
    except Exception as exc:
        add(results, "arith.table-parse-error", "arithmetic", False, repr(exc))

    release = re.search(r"R_session\s*=\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)\s*`?\s*shutter releases", flat)
    if release:
        base, extra, stated = map(int, release.groups())
        release_ok, release_ev = base == 891 and extra == 1 and stated == base + extra == 892, f"{base}+{extra}={stated}"
    else:
        release_ok, release_ev = False, "not parsed"
    add(results, "arith.release-total", "arithmetic", release_ok, release_ev)
    # Numeric residue and duration accounting.
    ok603, ev603 = only_allowed_number_occurrences(capture, "603", [
        "the 603-frame request **superseded**",
        "Superseded: the 603-frame design",
        "| Superseded frozen request | 603 | 443-frame automated-bracket session + 160-frame truth-reference block |",
    ])
    add(results, "numbers.603-only-historical", "numeric-residue", ok603, ev603)
    ok160, ev160 = only_allowed_number_occurrences(capture, "160", [
        "Superseded amendment: 2026-09 (160-frame truth reference and 1.30x main setting)",
        "| Superseded frozen request | 603 | 443-frame automated-bracket session + 160-frame truth-reference block |",
        "Replace the superseded 160-frame reference block with the 448-frame inverted block",
        "replace the superseded 160-frame reference with the decomposed 448-frame inverted block",
    ])
    add(results, "numbers.160-only-historical", "numeric-residue", ok160, ev160)
    add(results, "numbers.no-604-release", "numeric-residue", re.search(r"(?<!\d)604(?!\d)", capture) is None, "old release total absent")
    add(results, "numbers.no-N-M135", "numeric-residue", "N_M135" not in capture, "no unresolved count placeholder")
    add(results, "numbers.no-old-floor", "numeric-residue", "18.4" not in capture and "22.6" not in capture, "old floor absent")

    bracket_frames = sum_labels(mapping, BRACKETS) if mapping else None
    bracket_intervals = sum((mapping.get(label, (0, ""))[0] or 0) - 1 for label in BRACKETS) if mapping else None
    nonbracket = facts.get("physical_sum") - bracket_frames if isinstance(facts.get("physical_sum"), int) and isinstance(bracket_frames, int) else None
    duration = re.search(r"fixed scored blocks include (\d+) automated-bracket frames in (nine|\d+) passes, hence (\d+) three-second intervals, and (\d+) non-bracket exposures", lower)
    duration_values = None
    if duration:
        passes = 9 if duration.group(2) == "nine" else int(duration.group(2))
        duration_values = (int(duration.group(1)), passes, int(duration.group(3)), int(duration.group(4)))
    add(results, "numbers.duration.bracket-frames", "numeric-residue", duration_values is not None and duration_values[0] == bracket_frames == 419, f"parsed={duration_values} derived={bracket_frames}")
    add(results, "numbers.duration.pass-count", "numeric-residue", duration_values is not None and duration_values[1] == len(BRACKETS) == 9, f"parsed={duration_values}")
    add(results, "numbers.duration.intervals", "numeric-residue", duration_values is not None and duration_values[2] == bracket_intervals == 410, f"parsed={duration_values} derived={bracket_intervals}")
    add(results, "numbers.duration.nonbracket", "numeric-residue", duration_values is not None and duration_values[3] == nonbracket == 472, f"parsed={duration_values} derived={nonbracket}")

    formula1 = re.search(r"\((\d+) x 3 s \+ (\d+) x 1 s \+ (\d+) terminal bracket exposures x 1 s\) / 60 = ([0-9.]+) min", flat)
    f1_ok, f1_ev = False, "not parsed"
    if formula1:
        intervals, singles, terminals = map(int, formula1.groups()[:3])
        stated = float(formula1.group(4)); computed = (intervals * 3 + singles + terminals) / 60
        f1_ok = (intervals, singles, terminals) == (410, 472, 9) and math.isclose(stated, computed, abs_tol=0.0051)
        f1_ev = f"computed={computed:.6f} stated={stated:.2f}"
    add(results, "numbers.duration.floor-inclusive", "numeric-residue", f1_ok, f1_ev)
    formula2 = re.search(r"\((\d+) x 3 s \+ (\d+) x 1 s \+ (\d+) x 1 s\) / 60 = ([0-9.]+) min", flat)
    f2_ok, f2_ev = False, "not parsed"
    if formula2:
        intervals, bracket_exp, singles = map(int, formula2.groups()[:3])
        stated = float(formula2.group(4)); computed = (intervals * 3 + bracket_exp + singles) / 60
        f2_ok = (intervals, bracket_exp, singles) == (410, 419, 472) and math.isclose(stated, computed, abs_tol=0.0051)
        f2_ev = f"computed={computed:.6f} stated={stated:.2f}"
    add(results, "numbers.duration.floor-additive", "numeric-residue", f2_ok, f2_ev)
    floor_range = re.search(r"acquisition floor is \*\*([0-9.]+)-([0-9.]+) minutes\*\*", flat)
    add(results, "numbers.duration.range", "numeric-residue", bool(floor_range and tuple(map(float, floor_range.groups())) == (28.5, 35.4)), f"range={floor_range.groups() if floor_range else None}")
    slack = re.search(r"leaves only ([0-9.]+)-([0-9.]+) minutes inside a 45-minute sitting", flat)
    slack_ok = bool(slack and float(slack.group(1)) <= 45 - 35.35 < float(slack.group(1)) + 0.1 and math.isclose(float(slack.group(2)), 45 - 28.52, abs_tol=0.03))
    add(results, "numbers.duration.slack", "numeric-residue", slack_ok, f"slack={slack.groups() if slack else None}")
    add(results, "numbers.old-duration-labelled-unsafe", "numeric-residue", "The former 45-60-minute estimate is no longer a safe planning assumption" in flat, "old estimate explicitly rejected")

    # M_work is a placeholder, never an instruction with a numeric default.
    add(results, "mwork.banner-unset", "working-magnification", "parameter `M_work` remains unset" in capture, "banner says unset")
    add(results, "mwork.change-row-unset", "working-magnification", "Leave `M_work` unset until M147 supplies it" in capture, "change table says unset")
    add(results, "mwork.settings-placeholder", "working-magnification", "use the bare lens at **`M_work`**, an explicitly unset" in capture, "settings use placeholder")
    add(results, "mwork.supplied-by-preflight", "working-magnification", "M147-supplied `M_work`" in flat and "Copy the supplied `M_work` value" in flat, "operational value comes from M147")
    add(results, "mwork.no-1.32", "working-magnification", "1.32" not in capture, "no 1.32 default")
    add(results, "mwork.no-old-instruction", "working-magnification", "main sweeps at 1.30" not in lower and "sweeps and all witnesses: 1.30" not in lower, "old imperative absent")
    numeric_lines, forbidden_lines = [], []
    for number, line in enumerate(lines, 1):
        normalized = norm(line)
        if re.search(r"1\.3[023](?:x)?", normalized):
            numeric_lines.append(number)
            allowed = ("conditionally", "geometry", "not permission", "only if", "conditional calculation", "stated condition", "does not select", "superseded amendment")
            if not any(word in normalized.lower() for word in allowed):
                forbidden_lines.append(number)
    add(results, "mwork.no-concrete-instruction", "working-magnification", not forbidden_lines, f"numeric_lines={numeric_lines} forbidden={forbidden_lines}")
    assignments = [(n, norm(line)) for n, line in enumerate(lines, 1) if re.search(r"M_work\s*=\s*\d", line)]
    assignment_ok = all(any(word in text.lower() for word in ("conditionally", "only if", "stated condition")) for _, text in assignments)
    add(results, "mwork.assignments-conditional", "working-magnification", assignment_ok and len(assignments) == 3, f"assignments={[n for n, _ in assignments]}")

    # Converter inversion.
    forbidden_converter = bool(re.search(r"(?:keep|leave).{0,100}teleconverter.{0,100}(?:installed|fitted).{0,100}every frame", lower) or re.search(r"teleconverter (?:installed|fitted) for every frame", lower))
    add(results, "converter.no-all-frame-instruction", "converter-state", not forbidden_converter, f"forbidden_match={forbidden_converter}")
    add(results, "converter.banner-partition", "converter-state", "converter **on** for the existing session and the reference frames, then **off** for the TC0 scored sweeps" in flow, "banner partitions states")
    add(results, "converter.table-tc0-off", "converter-state", all("converter-on" not in mapping.get(label, (None, ""))[1].lower() for label in TC0_FOCUS + TC0_CAL) if mapping else False, "TC0 purposes are bare-lens")
    add(results, "converter.remove-before-tc0", "converter-state", "1. Remove the converter." in capture and "Only after every converter-on subject and calibration frame is complete" in capture, "single boundary")
    add(results, "converter.keep-off-tc0", "converter-state", "Keep it off for every TC0 sweep, TC0 witness, TC0 flat and TC0 dark" in flat, "TC0 stays bare")
    add(results, "converter.reference-on", "converter-state", "Leave the 2\u00d7 teleconverter on" in capture and "Converter-on truth reference" in capture, "reference stays converter-on")

    # STOP banner and its unweakened release conditions.
    stop_line = "> # \u26d4 STOP \u2014 THIS DOCUMENT IS NOT SAFE TO SHOOT FROM"
    add(results, "stop.exact-banner", "stop-banner", len(lines) >= 3 and lines[2] == stop_line, f"line3={lines[2] if len(lines) >= 3 else None}")
    add(results, "stop.body-reconciled", "stop-banner", "scored frame and release totals, block layout and converter inversion are reconciled" in flow_lower and "443-frame session and the 448-frame inverted block" in flow_lower, "body condition complete")
    add(results, "stop.preflight-open", "stop-banner", "preflight has not been delivered or rehearsed" in flow_lower, "preflight remains open")
    add(results, "stop.rehearsal-open", "stop-banner", "non-holdout rehearsal required by blockers 1 and 2 has not been completed" in flow_lower, "rehearsal remains open")
    required_removal = norm("This banner is removed only after M147's preflight has been delivered and rehearsed and the exact-configuration non-holdout rehearsal has closed blockers 1 and 2, including the physical control arms. DO NOT SHOOT until the orchestrator removes this banner.")
    add(results, "stop.removal-condition", "stop-banner", required_removal in flow, "requires delivered/rehearsed preflight and rehearsal closure")
    add(results, "stop.not-softened", "stop-banner", "banner may be removed before" not in lower and "safe to shoot" not in lower.replace("not safe to shoot", ""), "no permissive language")
    add(results, "stop.status-blocked", "stop-banner", "Status: **BLOCKED" in capture and "DO NOT SHOOT" in capture, "status blocked")
    # Physical controls are explicitly outside the scored manifest.
    control_rows = [label for label in physical_labels if re.search(r"control|ctrl|m135", label, re.I)]
    control_purposes = [label for label in physical_labels if re.search(r"control arm|m135|ctrl-", mapping.get(label, (None, ""))[1], re.I)] if mapping else []
    add(results, "controls.no-scored-table-row", "control-arms", not control_rows and not control_purposes, f"labels={control_rows} purposes={control_purposes}")
    add(results, "controls.fixed-scored-total", "control-arms", facts.get("stated_total") == 891 and "N_M135" not in capture, "no control increment")
    add(results, "controls.rehearsal-only-heading", "control-arms", "NON-HOLDOUT REHEARSAL ONLY" in capture, "section is exclusionary")
    add(results, "controls.explicit-prohibition", "control-arms", "DO NOT ACQUIRE OR READ THESE CONTROLS IN THE SCORED SESSION" in capture, "scored acquisition forbidden")
    add(results, "controls.external-acquisition", "control-arms", "These arms must be acquired and read in the non-holdout rehearsal" in capture, "assigned outside holdout")
    add(results, "controls.no-posthoc-selection", "control-arms", "Do not select the blur arm after the fact from this session's" in capture, "selection forbidden")
    add(results, "controls.no-reference-as-arm", "control-arms", "Do not use the converter-on truth reference measured against the TC0 scored" in capture, "circular arm forbidden")
    add(results, "controls.no-addition", "control-arms", "Do not add either control to the scored block table" in capture, "manifest addition forbidden")

    # Internal block/prose consistency.
    shoot_steps = [int(m.group(1)) for line in lines if (m := re.match(r"### (\d+)\.", line))]
    add(results, "internal.shooting-step-sequence", "internal-consistency", shoot_steps == list(range(10)), f"steps={shoot_steps}")
    gate_steps = [m.group(1) for line in lines if (m := re.match(r"### (G[0-3])\b", line))]
    add(results, "internal.gate-sequence", "internal-consistency", gate_steps == ["G0", "G1", "G2", "G3"], f"gates={gate_steps}")
    add(results, "internal.section5-count", "internal-consistency", "### 5. Converter-on truth reference \u2014 96 frames" in capture and sum_labels(mapping, REFERENCE) == 96, "heading matches rows")
    add(results, "internal.section8-count", "internal-consistency", "### 8. TC0 scored pairs and witnesses \u2014 224 frames" in capture and (sum_labels(mapping, TC0_FOCUS) or 0) + (sum_labels(mapping, TC0_WITNESSES) or 0) == 224, "heading matches 164+60")
    add(results, "internal.section9-count", "internal-consistency", "### 9. TC0 calibration \u2014 128 frames" in capture and sum_labels(mapping, TC0_CAL) == 128, "heading matches rows")
    add(results, "internal.converter-443", "internal-consistency", (sum_labels(mapping, CONVERTER_FOCUS + CONVERTER_CAL) or 0) + (sum_labels(mapping, CONVERTER_WITNESSES) or 0) == 443, "383+60=443")
    add(results, "internal.inverted-448", "internal-consistency", (sum_labels(mapping, REFERENCE + TC0_FOCUS + TC0_WITNESSES + TC0_CAL) or 0) == 448, "96+164+60+128=448")
    add(results, "internal.one-throwaway", "internal-consistency", "One throwaway histogram exposure precedes the scored session and is not in" in flat and "test exposure is not part of `T_session`" in flat, "throwaway excluded")
    add(results, "internal.calibration-counts", "internal-consistency", "Flats \u2014 32 for A and 32 for B in each optical state, 128 total" in capture and "Darks \u2014 32 for A and 32 for B in each optical state, 128 total" in capture, "state/A-B totals agree")
    add(results, "internal.dark-discards", "internal-consistency", "eight discarded settling darks" in lower and "first two frames of each group" in lower and "four named dark groups" in lower, "4x2=8")
    add(results, "internal.repeat-sections-exist", "internal-consistency", "repeat sections 1-3 under the tc0-prefixed names" in lower and shoot_steps[:4] == [0, 1, 2, 3], "sections 1-3 exist")
    identifier_pattern = re.compile(r"(?<![A-Za-z0-9-])(?:TC0-)?(?:P[01]|S(?:4|10)-[A-Z]|E(?:4|10)-[A-Z]|sw(?:10|4|1)(?:-[A-Z])?|FLAT-[A-Z]|DARK-[A-Z]|CTRL-[A-Z]+)(?![A-Za-z0-9-])|TR-REF-[A-Z]+")
    seen_ids = {m.group(0) for m in identifier_pattern.finditer(capture)}
    unknown_ids = sorted(seen_ids - KNOWN_IDS)
    add(results, "internal.no-unknown-block-identifiers", "internal-consistency", not unknown_ids, f"unknown={unknown_ids}")
    add(results, "internal.reference-blocks-in-prose", "internal-consistency", all(capture.count(f"`{name}`") >= 2 for name in REFERENCE), "TR rows named outside table")
    add(results, "internal.converter-blocks-covered", "internal-consistency", all(fragment in capture for fragment in ["`P0`", "`P1`", "`S4-A`", "`E4-A`", "`S4-B`", "`E4-B`", "`S10-A`", "`E10-A`", "`S10-B`", "`E10-B`", "`sw1`"]), "converter rows named")
    add(results, "internal.tc0-groups-covered", "internal-consistency", all(fragment in capture for fragment in ["`TC0-P0/P1`", "`TC0-S4-A`", "`TC0-S10-B`", "`TC0-sw4-A/B`", "`TC0-sw10-A/B`", "`TC0-FLAT-A/B`", "`TC0-DARK-A/B`"]), "TC0 rows named individually or collectively")
    manifest_fragments = ["eight converter-on start/end bursts of six", "`sw4-A/B` at 55 each", "`sw10-A/B` at 27 each", "`sw1` at 91", "four converter-on calibration groups at 32 each", "`TR-REF-NEAR/MID/FAR` at 32 each", "eight TC0 start/end bursts of six", "`TC0-sw4-A/B` at 55 each", "`TC0-sw10-A/B` at 27 each", "four TC0 calibration groups at 32 each"]
    add(results, "internal.manifest-covers-table", "internal-consistency", all(norm(fragment) in flat for fragment in manifest_fragments), "arrival manifest covers groups")

    # Every file/range cross-reference must resolve literally and substantively.
    citations = list(re.finditer(r"`([^`\n]*\.md):(\d+)(?:-(\d+))?`", capture))
    add(results, "xref.count", "internal-consistency", len(citations) == 4, f"citations={len(citations)}")
    literal_flags, bounds_flags, citation_details = [], [], []
    for match in citations:
        raw_path, start, end = match.group(1), int(match.group(2)), int(match.group(3) or match.group(2))
        resolved, literal, match_count = resolve_reference(raw_path)
        literal_flags.append(literal)
        in_bounds = False
        if resolved:
            in_bounds = 1 <= start <= end <= len(read_utf8(resolved).splitlines())
        bounds_flags.append(in_bounds)
        citation_details.append(f"{raw_path}:{start}-{end}:literal={literal}:matches={match_count}:bounds={in_bounds}")
    add(results, "xref.paths-resolve-literally", "internal-consistency", len(citations) == 4 and all(literal_flags), "; ".join(citation_details))
    add(results, "xref.ranges-in-bounds", "internal-consistency", len(citations) == 4 and all(bounds_flags), "; ".join(citation_details))

    def cited_range_for_phrase(phrase: str) -> tuple[str | None, str]:
        phrase_pos = lower.find(norm(phrase).lower())
        if phrase_pos < 0:
            return None, "phrase absent"
        cite = re.search(r"`([^`]*\.md):(\d+)-(\d+)`", flat[phrase_pos:])
        if not cite:
            return None, "citation absent"
        resolved, _, match_count = resolve_reference(cite.group(1))
        if not resolved:
            return None, f"path matches={match_count}"
        source_lines = read_utf8(resolved).splitlines()
        start, end = int(cite.group(2)), int(cite.group(3))
        if not (1 <= start <= end <= len(source_lines)):
            return None, f"range={start}-{end} out of bounds"
        return norm(" ".join(source_lines[start - 1:end])), f"{cite.group(1)}:{start}-{end}"

    commission_phrase = "may commission a new instrument but may never provide its scored value"
    commission_source, commission_ref = cited_range_for_phrase(commission_phrase)
    add(results, "xref.commission-quote", "internal-consistency", commission_source is not None and norm(commission_phrase).lower() in commission_source.lower(), commission_ref)
    frequency_phrase = "no frequency above `0.25 cyc/native px`"
    frequency_source, frequency_ref = cited_range_for_phrase(frequency_phrase)
    add(results, "xref.frequency-quote", "internal-consistency", frequency_source is not None and norm(frequency_phrase).lower() in frequency_source.lower(), frequency_ref)
    holdout_cites = [detail for detail in citation_details if ":345-349:" in detail]
    add(results, "xref.holdout-rule", "internal-consistency", len(holdout_cites) == 2 and actual_holdout == expected_holdout, f"matching_citations={len(holdout_cites)}")

    facts["physical_rows"] = [(label, mapping.get(label, (None, ""))[0]) for label in PHYSICAL]
    facts["failed"] = [result for result in results if not result.passed]
    return results, facts
def replace_unique_line(text: str, anchor: str, replacement: str, label: str) -> str:
    lines = text.splitlines()
    count = sum(line == anchor for line in lines)
    if count != 1:
        raise RuntimeError(f"mutation {label}: anchor count is {count}, expected exactly 1: {anchor!r}")
    output: list[str] = []
    for line in lines:
        output.extend(replacement.split("\n")) if line == anchor else output.append(line)
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")

def corrected_fixture(text: str) -> str:
    text = replace_unique_line(
        text,
        'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md:462-463`).',
        'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md:577-578`).',
        "fix-commission-citation",
    )
    return replace_unique_line(
        text,
        'above `0.25 cyc/native px`"* (`2026-09-sota-scorecard.md:465-467`) \u2014 and SOTA',
        'above `0.25 cyc/native px`"* (`docs/proposals/2026-09-sota-scorecard.md:581-582`) \u2014 and SOTA',
        "fix-frequency-citation",
    )

@dataclass(frozen=True)
class Mutation:
    name: str
    defect_class: str
    anchor: str
    replacement: str
    expected_failed: tuple[str, ...]
    inert: bool = False

def commission(capture_path: Path) -> int:
    clean = corrected_fixture(read_utf8(capture_path))
    mutations = [
        Mutation("arithmetic-block-count", "arithmetic",
            "| `TC0-sw10-B` | 27 | identical independent repeat of `TC0-sw10-A` |",
            "| `TC0-sw10-B` | 26 | identical independent repeat of `TC0-sw10-A` |",
            ("arith.physical.TC0-sw10-B", "arith.physical-sum", "arith.stated-total")),
        Mutation("arithmetic-stated-total", "arithmetic",
            "| **scored session total `T_session`** | **891** | `383 + 60 + 96 + 164 + 60 + 128` |",
            "| **scored session total `T_session`** | **890** | `383 + 60 + 96 + 164 + 60 + 128` |",
            ("arith.stated-total", "arith.total-expression")),
        Mutation("stale-603-wrapped", "numeric-residue",
            "Superseded: the 603-frame design, on 2026-09-04",
            "Current session total is 603\nframes.",
            ("numbers.603-only-historical",)),
        Mutation("stale-duration-budget", "numeric-residue",
            "promise 45 minutes.** The fixed scored blocks include 419 automated-bracket",
            "promise 45 minutes.** The fixed scored blocks include 255 automated-bracket",
            ("numbers.duration.bracket-frames",)),
        Mutation("mwork-silent-default", "working-magnification",
            "- **TC0 phase:** use the bare lens at **`M_work`**, an explicitly unset",
            "- **TC0 phase:** use the bare lens at **1.30x**, a silently defaulted setting",
            ("mwork.settings-placeholder", "mwork.no-concrete-instruction")),
        Mutation("converter-every-frame-wrapped", "converter-state",
            "off for every TC0 sweep, TC0 witness, TC0 flat and TC0 dark. This is an optical",
            "Keep the teleconverter installed for every\nframe in the session. This is an optical",
            ("converter.no-all-frame-instruction", "converter.keep-off-tc0")),
        Mutation("stop-banner-removed", "stop-banner",
            "> # \u26d4 STOP \u2014 THIS DOCUMENT IS NOT SAFE TO SHOOT FROM",
            "> # READY TO SHOOT", ("stop.exact-banner",)),
        Mutation("stop-condition-softened", "stop-banner",
            "> **This banner is removed only after M147's preflight has been delivered and",
            "> **This banner may be removed before M147's preflight has been delivered and",
            ("stop.removal-condition", "stop.not-softened")),
        Mutation("control-row-in-scored-table", "control-arms",
            "| **existing claim/calibration** | **383** | 255 converter-on focus + 128 converter-on calibration |",
            "| `TC0-CTRL-BLUR` | 32 | scored-session physical blur control |\n| **existing claim/calibration** | **383** | 255 converter-on focus + 128 converter-on calibration |",
            ("controls.no-scored-table-row", "arith.physical-row-order", "internal.no-unknown-block-identifiers")),
        Mutation("unknown-block-reference", "internal-consistency",
            "`TC0-S10-B`, `TC0-sw10-B`, `TC0-E10-B`. Use the same counts, direction,",
            "`TC0-S10-B`, `TC0-sw10-B`, `TC0-E10-C`. Use the same counts, direction,",
            ("internal.no-unknown-block-identifiers",)),
        Mutation("stale-cross-reference", "internal-consistency",
            'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md:577-578`).',
            'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md:1-2`).',
            ("xref.commission-quote",)),
        Mutation("missing-block-purpose", "internal-consistency",
            "| reset pre-flight `P0` | 6 | converter on, fixed focus at the existing maximum-reproduction reset |",
            "| reset pre-flight `P0` | 6 | |", ("internal.all-block-purposes-present",)),
        Mutation("inert-owner-metadata", "placebo", "Owning lane: **lane-FRC**",
            "Owning lane: **lane-FRC** (administrative note)", (), inert=True),
    ]
    outcomes: list[bool] = []
    with tempfile.TemporaryDirectory(prefix="m156-capreq-") as temp_name:
        temp_dir = Path(temp_name)
        base_path = temp_dir / "candidate.md"
        base_path.write_text(clean, encoding="utf-8", newline="\n")
        base_results, _ = verify(base_path)
        base_failed = [r.check_id for r in base_results if not r.passed]
        emit(f"COMMISSION_BASE {'GREEN' if not base_failed else 'RED'} checks={len(base_results)} failures={len(base_failed)}")
        if base_failed:
            for check_id in base_failed:
                emit(f"  UNEXPECTED_BASE_FAILURE {check_id}")
            return 2
        for index, mutation in enumerate(mutations, 1):
            mutated = replace_unique_line(clean, mutation.anchor, mutation.replacement, mutation.name)
            mutant_path = temp_dir / f"mutant-{index:02d}.md"
            mutant_path.write_text(mutated, encoding="utf-8", newline="\n")
            mutant_results, _ = verify(mutant_path)
            failed = {r.check_id for r in mutant_results if not r.passed}
            if mutation.inert:
                passed = not failed
                emit(f"INERT {'GREEN' if passed else 'RED'} {mutation.name} failures={len(failed)}")
            else:
                expected = set(mutation.expected_failed)
                passed = bool(failed) and expected.issubset(failed)
                emit(f"MUTATION {'RED' if failed else 'GREEN'} {mutation.name} class={mutation.defect_class} expected_failed={len(expected)} observed_failures={len(failed)} covered={'yes' if passed else 'no'}")
                if not passed:
                    emit(f"  expected={sorted(expected)}")
                    emit(f"  failed={sorted(failed)}")
            outcomes.append(passed)
    covered = sum(outcomes)
    defect_total = sum(not m.inert for m in mutations)
    defect_covered = sum(ok for m, ok in zip(mutations, outcomes) if not m.inert)
    inert_total = sum(m.inert for m in mutations)
    inert_green = sum(ok for m, ok in zip(mutations, outcomes) if m.inert)
    emit(f"MUTATION_COVERAGE {covered}/{len(outcomes)} defect_red={defect_covered}/{defect_total} inert_green={inert_green}/{inert_total}")
    return 0 if covered == len(outcomes) else 1

def print_report(results: list[Result], facts: dict[str, object], verbose: bool) -> None:
    failures = [r for r in results if not r.passed]
    emit(f"CAPTURE_SHA256 {facts['sha256']}")
    emit(f"CHECKS total={len(results)} passed={len(results)-len(failures)} failed={len(failures)}")
    for defect_class in sorted({r.defect_class for r in results}):
        selected = [r for r in results if r.defect_class == defect_class]
        failed = sum(not r.passed for r in selected)
        emit(f"CLASS {defect_class} checks={len(selected)} passed={len(selected)-failed} failed={failed}")
    emit("BLOCK_TABLE")
    for label, count in facts.get("physical_rows", []):
        emit(f"  {label}: {count}")
    emit(f"BLOCK_SUM {facts.get('physical_sum')} STATED_TOTAL {facts.get('stated_total')}")
    for result in results if verbose else failures:
        emit(f"{'PASS' if result.passed else 'FAIL'} {result.check_id}: {result.evidence}")
    emit(f"VERDICT {'GREEN' if not failures else 'RED'}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--commission", action="store_true")
    args = parser.parse_args()
    if args.commission:
        return commission(args.capture.resolve())
    results, facts = verify(args.capture.resolve())
    print_report(results, facts, args.verbose)
    return 0 if all(r.passed for r in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())