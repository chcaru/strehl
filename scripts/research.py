"""Browse and search local research without moving reports or indexing build trees.

Run `python scripts/research.py --help`. Python standard library only.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ("report-index.md", "experiment-index.md")
# Navigation hints derived only from names/titles, never automatic verdicts.
TOPICS = (
    ("alignment", "Alignment and geometry", r"align\w*|geometry|geometric|registration|register\w*|breathing|warp\w*|resampl\w*|kernel\w*|lanczos|catmull|halfdrift|curvature|curved track|dpar\w*|track jitter|scale centre"),
    ("reconstruction", "Merge and reconstruction", r"merg\w*|reconstruct\w*|fusion|pyramid\w*|blend\w*|coherent\w*|source ownership|source pure|source field|radiance|deconvol\w*|wiener|estimator\w*|estimating"),
    ("focus", "Focus evidence and admission", r"focus\w*|tenengrad\w*|argmax|elect\w*|admission|gate\w*|selector\w*|selection|depth|bimodal\w*"),
    ("noise", "Noise and sensor calibration", r"noise\w*|sensor\w*|calibrat\w*|fpn|prnu|ptc|photon transfer|iso|dark|sigma|correlation|rho|gain\w*"),
    ("optics", "Optics and capture design", r"optic\w*|aperture\w*|diffraction|pupil\w*|capture\w*|lens|magnification|polariz\w*|polarisation|astig\w*|quincunx|veil\w*"),
    ("color-raw", "RAW, color and development", r"raw|cfa|colou?r\w*|chroma\w*|demosaic\w*|decode\w*|highlight\w*|clip\w*|exposure|photometr\w*|black subtraction|white balance|tiff|rgb|rb|lca|ca"),
    ("artifacts", "Artifacts and source visibility", r"occlusion|halo\w*|seam\w*|ghost\w*|glare|rim\w*|aura|veiling|patchwork|waxy|borde\w*|coverage|visibility|foreground|matte|defect\w*|dust|hot pixel\w*"),
    ("quality", "Detail metrics and ground truth", r"metric\w*|sharp\w*|detail\w*|quality|instrument\w*|uncertainty|confidence|resolution|mtf|frc|ground truth|groundtruth|reference|truth|slantedge|ruler|metrology|hull|overshoot"),
    ("systems", "Performance and execution", r"performance|speed|timing|memory|rss|worker\w*|sampler\w*|campaign\w*|budget|gpu|nvme\w*|parallel\w*|profil\w*|scratch|decode\w*|throughput|writeback|execution|rehearsal|cost|environment|build\w*|benchmark\w*"),
    ("architecture", "Architecture and extensions", r"architect\w*|plugin\w*|interface\w*|gear identity|rust|hardware|pipeline|contribution"),
    ("comparators", "Comparators and scorecards", r"comparator\w*|comparative|comparisons?|commercial|head to head|headtohead\w*|h2h\w*|sota|scorecard\w*|zerene|helicon|landscape|dominance|ratification"),
    ("integrity", "Verification and research integrity", r"verif\w*|review\w*|audit\w*|retract\w*|citation\w*|fold\w*|corpus|invariant\w*|protocol\w*|prereg\w*|adjudicat\w*|ruling|readiness|reconcil\w*|refusal|claim\w*|attribution|prior art|findings|commission\w*|freeze\w*|feasibil\w*"),
    ("general", "Other research and uncategorized notes", r"(?!)"),
)
SCENES = (
    ("marigold", r"marigold\w*"), ("printer", r"printer\w*"),
    ("mineral", r"mineral\w*|ore|opal\w*"), ("vitamin", r"vitamin\w*"),
    ("chip", r"chip\w*"), ("bee", r"bee\w*"),
    ("coffee", r"coffee\w*"), ("checker", r"checker\w*"),
    ("foam", r"foam\w*"), ("ruler", r"ruler\w*"),
)
KINDS = ("decision", "report", "result", "review", "plan", "note", "directory")

# Curated subject hints where historical IDs/headlines hide the actual question.
# These are navigation metadata, never an assertion that a result is current/valid.
TOPIC_OVERRIDES = {
    "docs/research/SYNTHESIS.md": ("architecture", "integrity"),
    "docs/research/M41-r3-kill-measured.md": ("reconstruction",),
    "docs/research/M-CAND1.md": ("quality",),
    "docs/research/M-CAND2.md": ("quality",),
    "docs/research/M-FLATNULL.md": ("quality", "noise"),
    "docs/research/M126-composite.md": ("reconstruction",),
    "docs/research/M136-m8-passability.md": ("quality", "comparators"),
    "docs/research/M136-m8-v15-execution-assessment.md": ("quality", "integrity"),
    "docs/research/M142-m8o-handover.md": ("quality",),
    "docs/research/M152-site-census.md": ("comparators", "optics"),
    "docs/research/M164-m1-admissibility.md": ("quality", "comparators"),
    "docs/research/M166-bar-definition-repairs.md": ("comparators",),
    "docs/research/M172-m12s-closure.md": ("systems",),
    "docs/research/m194h-pedestal-causality.md": ("focus", "noise"),
    "docs/research/M75-rb-asymmetry.md": ("noise", "color-raw"),
    "docs/research/M76c-floor-remainder.md": ("noise",),
    "docs/research/M78b-b6-fixture-repair.md": ("quality", "integrity"),
    "docs/research/M92-null-averaging.md": ("noise",),
    "docs/research/M97o-refused-frames.md": ("alignment",),
    "docs/research/V-DCNULL.md": ("quality",),
    "docs/research/V-ENVSURF.md": ("systems",),
    "docs/research/V-EYES.md": ("quality", "integrity"),
    "docs/research/V-LINEAR.md": ("comparators", "quality"),
    "docs/research/V-LINEAR2.md": ("comparators", "noise"),
    "docs/research/V-SOFTCHECK-bandqual.md": ("quality",),
}


def words(text):
    return re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)


def normalized(text):
    return " ".join(words(text))


def labels(path, title):
    name = normalized(path + " " + title)
    counts = [(slug, len(re.findall(r"\b(?:" + pattern + r")\b", name)))
              for slug, _label, pattern in TOPICS[:-1]]
    topics = tuple(slug for slug, count in counts if count)
    primary = max(counts, key=lambda pair: pair[1])[0] if topics else "general"
    scenes = tuple(slug for slug, pattern in SCENES
                   if re.search(r"\b(?:" + pattern + r")\b", name))
    if path in TOPIC_OVERRIDES:
        explicit = TOPIC_OVERRIDES[path]
        topics = tuple(dict.fromkeys(explicit + topics))
        primary = explicit[0]
    return topics or ("general",), primary, scenes


def kind_for(path):
    name = path.stem.casefold()
    if path.name == "SYNTHESIS.md":
        return "decision"
    name_words = set(words(name))
    plan_name = (bool(name_words & {"plan", "plans", "planning", "charter", "design"})
                 or any(w.startswith("prereg") for w in name_words)
                 or "pre registration" in normalized(name))
    if path.parts[0] == "experiments" and plan_name:
        return "plan"
    if re.search(r"review|verif|audit|adjudicat|ruling", name):
        return "review"
    if "decision" in name:
        return "decision"
    if path.parts[0] == "docs":
        return "report"
    if name.startswith("independent"):
        return "review"
    if "result" in name or "observation" in name:
        return "result"
    return "note"


@dataclass
class Document:
    path: str
    title: str
    text: str
    area: str
    kind: str
    topics: tuple
    primary: str
    scenes: tuple

    def metadata(self):
        return {k: getattr(self, k) for k in
                ("path", "title", "area", "kind", "topics", "primary", "scenes")}


def discover(root):
    """Bounded, explicit Markdown scopes; never recurse into outputs/snapshots."""
    paths = [p for p in (root / "docs/research").glob("*.md")
             if p.name.casefold() not in {"readme.md", *GENERATED}]
    paths += list((root / "experiments").glob("*.md"))
    for directory in sorted((root / "experiments").iterdir()) if (root / "experiments").is_dir() else []:
        if not directory.is_dir() or directory.is_symlink() or directory.name.startswith("."):
            continue
        markdown = list(directory.glob("*.md"))
        paths.extend(markdown)
        if not markdown:
            yield directory, True
    for path in sorted(set(paths)):
        if path.is_file() and not path.is_symlink():
            yield path, False


def load_documents(root):
    documents = []
    root = root.resolve()
    if not (root / "docs/research").is_dir():
        raise ValueError("No docs/research directory under " + str(root))
    for path, directory in discover(root):
        if not path.resolve().is_relative_to(root):
            raise ValueError("Research path escapes repository: " + str(path))
        rel = path.relative_to(root).as_posix()
        text = "" if directory else path.read_text(encoding="utf-8-sig")
        headline = re.search(r"^#\s+(.+)$", text, re.M)
        title = headline[1].strip() if headline else path.stem
        topics, primary, scenes = labels(rel, title)
        documents.append(Document(rel, title, text,
                                  "reports" if rel.startswith("docs/") else "experiments",
                                  "directory" if directory else kind_for(Path(rel)),
                                  topics, primary, scenes))
    return sorted(documents, key=lambda d: d.path.casefold())


def selected(doc, args):
    return ((args.area == "all" or doc.area == args.area)
            and (not args.topic or args.topic in doc.topics)
            and (not args.scene or args.scene in doc.scenes)
            and (not args.kind or doc.kind == args.kind))


def excerpt(line, terms, width=350):
    """Keep matching context visible even in the corpus's very long table rows."""
    if len(line) <= width:
        return line
    hit = next((m.start() for m in re.finditer(r"[^\W_]+", line)
                if m[0].casefold() in terms), 0)
    start = max(0, hit - width // 3)
    end = min(len(line), start + width)
    start = max(0, end - width)
    return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")


def search(documents, query, *, match_any=False, phrase=False):
    terms = list(dict.fromkeys(words(query)))
    if not terms:
        raise ValueError("Supply at least one searchable word.")
    phrase_text = normalized(query)
    found = []
    for doc in documents:
        path_tokens, title_tokens = Counter(words(doc.path)), Counter(words(doc.title))
        body_tokens = Counter(words(doc.text))
        present = [bool(path_tokens[t] or title_tokens[t] or body_tokens[t]) for t in terms]
        if not (any(present) if match_any else all(present)):
            continue
        if phrase and not any((" " + phrase_text + " ") in (" " + normalized(field) + " ")
                              for field in (doc.path, doc.title, doc.text)):
            continue
        heading_tokens = Counter(words(" ".join(
            l for l in doc.text.splitlines() if l.startswith("#"))))
        # Cap body repetition so a giant cross-referencing ledger cannot win by length.
        score = sum(100 * bool(path_tokens[t]) + 60 * bool(title_tokens[t])
                    + 10 * min(heading_tokens[t], 3) + min(body_tokens[t], 5)
                    for t in terms)
        matches = []
        for number, line in enumerate(doc.text.splitlines(), 1):
            line_words = set(words(line))
            hits = sum(t in line_words for t in terms)
            if hits:
                matches.append((hits, number, line.strip()))
        matches.sort(key=lambda item: (-item[0], item[1]))
        snippets = [{"line": n, "text": excerpt(line, set(terms))} for _hits, n, line in matches[:2]]
        found.append({**doc.metadata(), "score": score, "snippets": snippets})
    return sorted(found, key=lambda item: (-item["score"], item["path"].casefold()))


def cell(text):
    return re.sub(r"\s+", " ", text).replace("|", r"\|").replace("`", "")


def link(path, label):
    import posixpath
    dest = posixpath.relpath(path, "docs/research")
    return "[" + cell(label).replace("[", r"\[").replace("]", r"\]") + "](" + quote(dest, safe="/._-") + ")"


def catalog_header(title):
    return (f"# {title}\n\n"
            "Generated by `python scripts/research.py catalog`; edit the source documents or\n"
            "topic rules in `scripts/research.py`, then regenerate. [Research guide](README.md).\n\n"
            "Topics and roles use names/titles plus curated subject hints for navigation, not\n"
            "verdicts, freshness or evidence of execution. Read source amendments and reviews.\n\n"
            + " · ".join(f"[{label}](#{slug})" for slug, label, _ in TOPICS) + "\n")


def catalog_texts(documents):
    reports = [d for d in documents if d.area == "reports"]
    report = catalog_header("Research report index")
    report += f"\n{len(reports)} report/decision documents, each listed once under its primary topic.\n"
    for topic, label, _ in TOPICS:
        report += f'\n<a id="{topic}"></a>\n\n## {label}\n\n'
        report += "| Document | Role | Other topics |\n| --- | --- | --- |\n"
        for d in reports:
            if d.primary == topic:
                report += (f"| {link(d.path, Path(d.path).name)} — {cell(d.title)} | {d.kind} | "
                           + ", ".join(t for t in d.topics if t != topic) + " |\n")
    groups = defaultdict(list)
    notes = []
    for d in documents:
        if d.area == "experiments":
            (groups[Path(d.path).parts[1]] if len(Path(d.path).parts) > 2
             or d.kind == "directory" else notes).append(d)
    experiment = catalog_header("Experiment index")
    experiment += (f"\n{len(groups)} experiment directories. Entry links favor result, review and plan\n"
                   "filenames; they are representative, not a complete file list. Search covers all\n"
                   "Markdown immediately inside each directory. Directory-only rows have no such\n"
                   "Markdown and are searchable by name only. Nested output/build trees are excluded.\n")
    if notes:
        experiment += "\nRoot notes: " + ", ".join(link(d.path, Path(d.path).name) for d in notes) + ".\n"
    for topic, label, _ in TOPICS:
        experiment += f'\n<a id="{topic}"></a>\n\n## {label}\n\n'
        experiment += "| Experiment | Entry documents | Other topics |\n| --- | --- | --- |\n"
        for name, docs in sorted(groups.items(), key=lambda pair: pair[0].casefold()):
            # One representative title avoids filing every well-reviewed experiment
            # under integrity simply because it has many review documents.
            representative = min(docs, key=lambda d: (
                ("result", "decision", "plan", "note", "review", "directory").index(d.kind),
                len(Path(d.path).name), d.path.casefold()))
            _topics, primary, _scenes = labels(name, representative.title)
            topics = tuple(t[0] for t in TOPICS if any(t[0] in d.topics for d in docs))
            if primary != topic:
                continue
            entries = []
            for kind, limit in (("result", 2), ("decision", 1), ("review", 2), ("plan", 1), ("note", 1)):
                candidates = sorted((d for d in docs if d.kind == kind),
                                    key=lambda d: (len(Path(d.path).name), d.path.casefold()))
                entries.extend(candidates[:limit])
            refs = "; ".join(link(d.path, Path(d.path).name) for d in entries)
            if not refs:
                refs = "Directory only; no top-level Markdown"
            experiment += (f"| {link('experiments/' + name, name)} | {refs} | "
                           + ", ".join(t for t in topics if t != topic) + " |\n")
    return dict(zip(GENERATED, (report, experiment)))


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root (default: script's checkout)")
    commands = ap.add_subparsers(dest="command", required=True)
    for command in ("search", "browse"):
        sub = commands.add_parser(command)
        sub.add_argument("--area", choices=("all", "reports", "experiments"), default="all")
        sub.add_argument("--topic", choices=[t[0] for t in TOPICS])
        sub.add_argument("--scene", choices=[s[0] for s in SCENES])
        sub.add_argument("--kind", choices=KINDS)
        sub.add_argument("--limit", type=positive, default=12 if command == "search" else 50)
        sub.add_argument("--json", action="store_true")
        if command == "search":
            sub.add_argument("query", nargs="+")
            mode = sub.add_mutually_exclusive_group()
            mode.add_argument("--any", action="store_true", help="match any query word instead of all")
            mode.add_argument("--phrase", action="store_true", help="match the entire normalized phrase")
    commands.add_parser("topics")
    cat = commands.add_parser("catalog")
    cat.add_argument("--check", action="store_true", help="fail if generated navigation is stale; do not write")
    return ap


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = parser()
    args = ap.parse_args(argv)
    if args.command == "topics":
        for slug, label, _pattern in TOPICS:
            print(f"{slug:16} {label}")
        print("Scenes: " + ", ".join(slug for slug, _ in SCENES))
        return 0
    try:
        documents = load_documents(args.root)
        if args.command == "catalog":
            stale = []
            for name, content in catalog_texts(documents).items():
                path = args.root / "docs/research" / name
                if args.check:
                    if not path.exists() or path.read_text(encoding="utf-8") != content:
                        stale.append(path)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8", newline="\n")
                    print("Wrote " + str(path))
            if stale:
                for path in stale:
                    print("STALE: " + str(path))
                return 1
            if args.check:
                print("Research catalogs are up to date.")
            return 0
        docs = [d for d in documents if selected(d, args)]
        hits = (search(docs, " ".join(args.query), match_any=args.any, phrase=args.phrase)
                if args.command == "search" else [d.metadata() for d in docs])
        shown = hits[:args.limit]
        if args.json:
            print(json.dumps({"total": len(hits), "shown": len(shown), "results": shown}, indent=2))
        else:
            print(f"{len(hits)} matching documents; showing {len(shown)}. Roles/topics are navigation hints.")
            for hit in shown:
                print(f"\n{hit['path']} [{hit['kind']}; {', '.join(hit['topics'])}]")
                print("  " + hit["title"])
                for snippet in hit.get("snippets", []):
                    print(f"  {hit['path']}:{snippet['line']}: {snippet['text']}")
            if not hits:
                print("No matches within this documented scope/filter. Try --any, fewer terms or broader filters.")
                print("This is not evidence that no prior work exists elsewhere.")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        ap.exit(2, f"research: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
