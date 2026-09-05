from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN_REL = "docs/proposals/2026-08-sota-path.md"
SCORECARD_REL = "docs/proposals/2026-09-sota-scorecard.md"
M139_REL = "docs/research/M139-m12-campaign.md"
M169_REL = "docs/research/M169-ratification-stakes.md"
OWNER_ACTIONS_REL = "docs/OWNER-ACTIONS.md"
OWNER_QUESTIONS_REL = "docs/research/OWNER-QUESTIONS.md"
CLOSEOUT_REL = (
    "experiments/m12-scorecard/out/"
    "campaign-8009447e-m139/closeout.json"
)

INTRO_COMMIT = "986c46535fc082395831724f1d45c33a1d974390"
SPLIT_COMMIT = "dd957dd5f8ef36af99065db5aa52065171556adf"
PHRASES = (
    "must simultaneously pass M11",
    "while 16 workers passes M11",
    "M12-S",
)


def run_git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.stdout


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def source_fingerprint(rel: str) -> dict[str, object]:
    data = (ROOT / rel).read_bytes()
    text = data.decode("utf-8")
    return {
        "path": rel,
        "lines": len(text.splitlines()),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def line_hits(rel: str, pattern: str, flags: int = 0) -> list[dict[str, object]]:
    rx = re.compile(pattern, flags)
    return [
        {"line": number, "text": line}
        for number, line in enumerate(read(rel).splitlines(), 1)
        if rx.search(line)
    ]


def pickaxe(phrase: str) -> list[dict[str, str]]:
    output = run_git(
        "--no-pager",
        "log",
        "--all",
        "--date=iso-strict",
        "--format=%H%x09%ad%x09%s",
        f"-S{phrase}",
        "--",
        SCORECARD_REL,
    )
    rows = []
    for line in output.splitlines():
        commit, date, subject = line.split("\t", 2)
        rows.append({"commit": commit, "date": date, "subject": subject})
    return rows


def commit_metadata(commit: str) -> dict[str, str]:
    output = run_git(
        "--no-pager",
        "show",
        "-s",
        "--date=iso-strict",
        "--format=%H%x09%ad%x09%s%x09%b",
        commit,
    ).rstrip("\n")
    full_hash, date, subject, body = output.split("\t", 3)
    return {
        "commit": full_hash,
        "date": date,
        "subject": subject,
        "body": body.strip(),
    }


def historical_plan_phrase_hits() -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    revisions = run_git("rev-list", "--all", "--", PLAN_REL).splitlines()
    for revision in revisions:
        text = run_git("show", f"{revision}:{PLAN_REL}")
        collapsed = re.sub(r"\s+", " ", text)
        for phrase in PHRASES:
            if phrase in collapsed:
                hits.append({"revision": revision, "phrase": phrase})
    return hits


def current_proposal_phrase_hits() -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for path in sorted((ROOT / "docs" / "proposals").glob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for phrase in PHRASES[:2]:
                if phrase in line:
                    hits.append({"path": rel, "line": number, "phrase": phrase})
    return hits


def owner_record_candidates() -> list[str]:
    paths = run_git("ls-files", "docs").splitlines()
    return sorted(
        path
        for path in paths
        if re.search(r"owner|response|ratif", path, re.IGNORECASE)
    )


def explicit_owner_scorecard_ratification_hits() -> list[dict[str, object]]:
    patterns = [
        re.compile(
            r"\bowner\s+(?:has\s+)?(?:ratified|approved|accepted)\s+"
            r"(?:the\s+)?scorecard\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bscorecard\s+(?:has\s+been|was|is)\s+"
            r"(?:ratified|approved|accepted)\s+by\s+(?:the\s+)?owner\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bI\s+(?:ratify|approve|accept)\s+(?:the\s+)?scorecard\b",
            re.IGNORECASE,
        ),
    ]
    hits: list[dict[str, object]] = []
    for rel in run_git("ls-files", "docs").splitlines():
        path = ROOT / rel
        if path.suffix.lower() != ".md":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                hits.append({"path": rel, "line": number, "text": line})
    return hits


def main() -> None:
    plan = read(PLAN_REL)
    closeout = json.loads(read(CLOSEOUT_REL))
    verdicts = closeout["verdicts"]
    byte_by_n = verdicts["m12_s"]["byte_property_by_n"]

    plan_collapsed = re.sub(r"\s+", " ", plan)
    current_plan_hits = [
        phrase for phrase in PHRASES if phrase in plan_collapsed
    ]
    history_hits = historical_plan_phrase_hits()
    proposal_hits = current_proposal_phrase_hits()
    pickaxe_results = {
        phrase: pickaxe(phrase) for phrase in PHRASES[:2]
    }

    owner_questions_log = run_git(
        "--no-pager",
        "log",
        "-1",
        "--date=iso-strict",
        "--format=%H%x09%ad%x09%s",
        "--",
        OWNER_QUESTIONS_REL,
    ).strip()
    owner_q_hash, owner_q_date, owner_q_subject = owner_questions_log.split("\t", 2)

    result = {
        "schema": 1,
        "verdict": "UNRATIFIED_ADDITION",
        "source_fingerprints": [
            source_fingerprint(rel)
            for rel in (
                PLAN_REL,
                SCORECARD_REL,
                M139_REL,
                M169_REL,
                OWNER_ACTIONS_REL,
                OWNER_QUESTIONS_REL,
                CLOSEOUT_REL,
            )
        ],
        "plan_absence_checks": {
            "current_whitespace_collapsed_phrase_hits": current_plan_hits,
            "all_revision_phrase_hits": history_hits,
            "revision_count": len(
                run_git("rev-list", "--all", "--", PLAN_REL).splitlines()
            ),
        },
        "current_proposal_phrase_hits": proposal_hits,
        "decisive_source_lines": {
            "plan_d9_summary": line_hits(PLAN_REL, r"determinism decoupled from worker count"),
            "plan_d9_bytes": line_hits(PLAN_REL, r"Bytes are then invariant to worker count"),
            "plan_d15_bars": line_hits(PLAN_REL, r"memory ≤6 GiB warm; bytes invariant"),
            "plan_m12_measurable": line_hits(PLAN_REL, r"Two axes -- M8 and M12 --"),
            "scorecard_m12_row": line_hits(SCORECARD_REL, r"^\| M12 \| Memory, determinism"),
            "scorecard_attribution": line_hits(SCORECARD_REL, r"^M8, the M11 comparator"),
            "scorecard_m12_clause": line_hits(SCORECARD_REL, r"must simultaneously pass M11"),
            "scorecard_revision_1_1": line_hits(SCORECARD_REL, r"Revision 1\.1,"),
            "m169_reverse_ruling": line_hits(M169_REL, r"reverse full-axis dependency"),
            "m169_r9": line_hits(M169_REL, r"\*\*R9 — new\*\*"),
            "owner_pending_register": line_hits(
                OWNER_ACTIONS_REL, r"full ratification instrument is being prepared", re.I
            ),
            "owner_silence_not_ratification": line_hits(
                OWNER_ACTIONS_REL, r"not treat silence as ratification", re.I
            ),
        },
        "git_provenance": {
            "pickaxe": pickaxe_results,
            "introducing_commit": commit_metadata(INTRO_COMMIT),
            "current_wording_commit": commit_metadata(SPLIT_COMMIT),
        },
        "owner_ratification_search": {
            "explicit_wholesale_ratification_hits": (
                explicit_owner_scorecard_ratification_hits()
            ),
            "tracked_candidate_records": owner_record_candidates(),
            "owner_questions_scorecard_hits": line_hits(
                OWNER_QUESTIONS_REL, r"scorecard", re.I
            ),
            "owner_questions_last_commit": {
                "commit": owner_q_hash,
                "date": owner_q_date,
                "subject": owner_q_subject,
            },
        },
        "m139_machine_results": {
            "campaign_complete": closeout["campaign_status"]["registered_campaign_complete"],
            "m12_d": verdicts["m12_d"],
            "m12_s_byte_property_verdict": verdicts["m12_s"]["byte_property_verdict"],
            "distinct_hashes_by_n": {
                n: {
                    "output": values["distinct_output_sha256"],
                    "pixels": values["distinct_pixel_sha256"],
                }
                for n, values in sorted(byte_by_n.items())
            },
            "maximum_sampled_gib": closeout["absolute_bars"]["memory_ceiling"][
                "maximum_sampled_process_tree_private_committed_gib"
            ],
            "memory_bar_gib": closeout["absolute_bars"]["memory_ceiling"]["bar_gib"],
            "memory_bar_verdict": closeout["absolute_bars"]["memory_ceiling"]["verdict"],
            "memory_multiple": closeout["absolute_bars"]["memory_ceiling"][
                "maximum_sampled_process_tree_private_committed_gib"
            ]
            / closeout["absolute_bars"]["memory_ceiling"]["bar_gib"],
            "n_mod_4_spread": closeout["absolute_bars"]["n_mod_4"]["spread"],
            "n_mod_4_bar": closeout["absolute_bars"]["n_mod_4"]["bar"],
            "n_mod_4_verdict": closeout["absolute_bars"]["n_mod_4"]["verdict"],
            "mechanical_m12": verdicts["frozen_registration_mechanical_result"],
            "orchestrator_directed_m12": verdicts["overall_m12"],
        },
    }

    assert not current_plan_hits
    assert not history_hits
    assert {
        (hit["path"], hit["phrase"]) for hit in proposal_hits
    } == {
        (SCORECARD_REL, PHRASES[0]),
        (SCORECARD_REL, PHRASES[1]),
    }
    assert pickaxe_results[PHRASES[0]][-1]["commit"] == INTRO_COMMIT
    assert pickaxe_results[PHRASES[1]][-1]["commit"] == SPLIT_COMMIT
    assert verdicts["m12_d"]["verdict"] == "PASS"
    assert verdicts["m12_s"]["byte_property_verdict"] == "FAIL"
    assert all(
        values["distinct_output_sha256"] == 5
        and values["distinct_pixel_sha256"] == 5
        for values in byte_by_n.values()
    )
    assert closeout["absolute_bars"]["memory_ceiling"]["verdict"] == "FAIL"
    assert closeout["absolute_bars"]["n_mod_4"]["verdict"] == "FAIL"
    assert verdicts["frozen_registration_mechanical_result"]["verdict"] == "FAIL"
    assert result["decisive_source_lines"]["m169_r9"]
    assert result["decisive_source_lines"]["owner_pending_register"]
    assert result["decisive_source_lines"]["owner_silence_not_ratification"]
    assert not result["owner_ratification_search"][
        "explicit_wholesale_ratification_hits"
    ]
    assert not result["owner_ratification_search"]["owner_questions_scorecard_hits"]

    output = Path(__file__).with_name("audit.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS: UNRATIFIED_ADDITION; no plan revision contains the conjunct; "
        "M139 machine result is M12-D PASS with byte, memory, and modulo FAIL."
    )


if __name__ == "__main__":
    main()
