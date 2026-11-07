"""Read-only source audit of root-scheduled final checks; writes only this lane's receipt."""
import collections
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_suffix('.json')
BASE = 'c149e52834fc1c86c2af0fe022713c39fa25f33c'
REVIEW = ROOT / 'experiments/multi-stack-2026-10-28/review'


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), '--work-tree=' + str(ROOT), *args], capture_output=True, check=True).stdout


assert git('rev-parse', 'origin/main').decode().strip() == BASE
cache = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(file):
    if file not in cache:
        run = subprocess.run(['git', '-C', str(ROOT), '--work-tree=' + str(ROOT), 'show', BASE + ':' + file], capture_output=True)
        baseline = run.stdout if run.returncode == 0 else None
        if baseline is None:
            # Missing files can be new source; other git failures must not masquerade as that.
            assert b'does not exist in' in run.stderr or b'exists on disk, but not in' in run.stderr, run.stderr
        current = (ROOT / file).read_bytes()
        before = baseline.decode('utf-8-sig').splitlines() if baseline is not None else None
        after = current.decode('utf-8-sig').splitlines()
        blocks = difflib.SequenceMatcher(None, before, after, autojunk=False).get_matching_blocks() if before is not None else []
        cache[file] = {'baseline_bytes': baseline, 'current_bytes': current, 'before': before, 'after': after, 'blocks': blocks}
    return cache[file]


def locations(lines, text):
    if not lines or not text:
        return []
    return [i + 1 for i in range(len(lines) - len(text) + 1) if lines[i:i + len(text)] == text]


def norm(file):
    path = Path(file.removeprefix('\\\\?\\'))
    return (path if path.is_absolute() else ROOT / path).resolve().relative_to(ROOT).as_posix()


def lint_audit():
    file = ROOT / 'outputs/multi-stack/frontend-clippy-4.jsonl'
    raw = file.read_bytes()
    records = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip().startswith('{')]
    messages = [r['message'] for r in records if r.get('reason') == 'compiler-message' and r['message']['level'] in ('warning', 'error')]
    found = {}
    for msg in messages:
        spans = [s for s in msg['spans'] if s['is_primary']]
        key = json.dumps([msg.get('code'), msg['message'], [(norm(s['file_name']), s['line_start'], s['column_start'], s['line_end'], s['column_end'], s['text']) for s in spans]], sort_keys=True)
        if key in found:
            found[key]['occurrences'] += 1
            continue
        item = {'code': (msg.get('code') or {}).get('code'), 'message': msg['message'], 'level': msg['level'], 'occurrences': 1, 'spans': []}
        for s in spans:
            path = norm(s['file_name'])
            src = source(path)
            text = [t['text'] for t in s['text']]
            cur_locs = locations(src['after'], text)
            matches = [{'current_start': loc, 'baseline_start': a + loc - b, 'unchanged_block_lines': n} for loc in cur_locs for a, b, n in src['blocks'] if b <= loc - 1 and loc - 1 + len(text) <= b + n]
            item['spans'].append({'file': path, 'reported_line': s['line_start'], 'reported_end': s['line_end'], 'column': s['column_start'], 'end_column': s['column_end'], 'text': text, 'baseline_locations': locations(src['before'], text), 'current_locations': cur_locs, 'current_file_sha256': sha(src['current_bytes']), 'diff_evidence': {'kind': 'entire_file_equals_baseline' if src['before'] == src['after'] else 'unchanged_diff_block' if matches else 'changed_or_new_span', 'mappings': matches}})
        item['classification'] = 'baseline_exact_span' if spans and all(s['baseline_locations'] and s['diff_evidence']['kind'] != 'changed_or_new_span' for s in item['spans']) else 'unmatched_or_new'
        if item['code'] == 'clippy::large_enum_variant' and item['spans'][0]['file'] == 'crates/strehl-cli/src/lib.rs':
            src = source('crates/strehl-cli/src/lib.rs')
            def variant(lines):
                a = lines.index('    Stack {')
                b = lines.index('    },', a)
                return lines[a:b + 1]
            align = source('crates/strehl-cli/src/align_cmd.rs')
            assert variant(src['before']) == variant(src['after'])
            assert '    Align(align_cmd::AlignArgs),' in src['before']
            assert align['baseline_bytes'] == align['current_bytes'].replace(b'\r\n', b'\n')
            labels = [(s.get('label'), [t['text'] for t in s['text']]) for s in msg['spans'] if s.get('label')]
            assert any('largest variant contains at least 644 bytes' in label and text[0].strip() == 'Stack {' for label, text in labels)
            assert any('second-largest variant contains at least 232 bytes' in label and text[0].strip() == 'Align(align_cmd::AlignArgs),' for label, text in labels)
            item['classification'] = 'inherited_variant_size_cause'
            item['manual_evidence'] = 'Diagnostic still names Stack (644 bytes) and Align (232 bytes). Entire Stack variant text and AlignArgs defining file (after checkout CRLF-to-LF conversion only) match baseline; Session is not a named size cause.'
        found[key] = item
    entries = list(found.values())
    old_file = REVIEW / 'lint-span-audit-3.json'
    previous = json.loads(old_file.read_bytes())[0]
    def signature(item):
        return json.dumps([item['code'], item['message'], [(s['file'], s['column'], s['text'] if item['code'] != 'clippy::large_enum_variant' else 'inherited_size_cause') for s in item['spans']]], sort_keys=True)
    old_sig = {signature(x) for x in previous['diagnostics']}
    new_sig = {signature(x) for x in entries}
    return {'input': file.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'compiler_message_records': len(messages), 'unique_diagnostics': len(entries), 'duplicate_records': len(messages) - len(entries), 'levels': dict(collections.Counter(x['level'] for x in messages)), 'build_finished': [r for r in records if r.get('reason') == 'build-finished'], 'classification_counts': dict(collections.Counter(x['classification'] for x in entries)), 'by_source_group': dict(collections.Counter('experiment_include' if x['spans'] and x['spans'][0]['file'].startswith('experiments/') else 'crate_source' for x in entries)), 'previous_audit': {'path': old_file.relative_to(ROOT).as_posix(), 'sha256': sha(old_file.read_bytes()), 'new_signatures': [json.loads(s) for s in sorted(new_sig - old_sig)], 'removed_signatures': [json.loads(s) for s in sorted(old_sig - new_sig)]}, 'diagnostics': entries}


def format_audit():
    file = ROOT / 'outputs/multi-stack/checks/engine-fmt-2.log'
    raw = file.read_bytes()
    text = raw.decode('utf-8-sig')
    headers = list(re.finditer(r'^Diff in (.+):(\d+):\r?$', text, re.M))
    results = []
    for n, h in enumerate(headers):
        path = norm(h.group(1))
        src = source(path)
        body = text[h.end():headers[n + 1].start() if n + 1 < len(headers) else len(text)].splitlines()
        old, removed, added = [], [], []
        for line in body:
            if line.startswith('+'):
                added.append(line[1:])
            if line.startswith(' ') or line.startswith('-'):
                if line.startswith('-'):
                    removed.append(len(old))
                old.append(line[1:])
        positions = locations(src['after'], old)
        baseline_positions = locations(src['before'], old)
        # rustfmt displays one virtual empty context line at a newline-terminated EOF.
        eof_context = False
        if not positions and src['current_bytes'].endswith(b'\n'):
            positions = locations(src['after'] + [''], old)
            eof_context = bool(positions)
        if not baseline_positions and src['baseline_bytes'] is not None and src['baseline_bytes'].endswith(b'\n'):
            baseline_positions = locations(src['before'] + [''], old)
        entry = {'virtual_eof_context': eof_context, 'file': path, 'reported_line': int(h.group(2)), 'current_file_sha256': sha(src['current_bytes']), 'input_hunk_lines': old, 'removed_offsets': removed, 'formatted_added_lines': added, 'current_locations': positions, 'baseline_locations': baseline_positions}
        if not positions:
            entry['classification'] = 'requires_review_current_span_not_found'
        elif src['before'] == src['after']:
            entry['classification'] = 'inherited_entire_file'
        else:
            at = min(positions, key=lambda p: abs(p - int(h.group(2)))) - 1
            changed, unchanged = [], []
            for offset in removed:
                idx = at + offset
                hits = [(a + idx - b + 1, n) for a, b, n in src['blocks'] if b <= idx < b + n]
                if hits:
                    unchanged.append({'current_line': idx + 1, 'baseline_line': hits[0][0]})
                else:
                    changed.append({'current_line': idx + 1, 'text': src['after'][idx]})
            entry['new_removed_lines'] = changed
            entry['unchanged_removed_lines'] = unchanged
            entry['classification'] = 'new_or_changed_formatting' if changed else 'inherited_removed_lines_map_to_baseline' if removed else 'inherited_insert_only_hunk' if baseline_positions else 'requires_review_insert_only_hunk'
        results.append(entry)
    new_lines = {line['text'] for e in results for line in e.get('new_removed_lines', [])}
    for e in results:
        if e['classification'] == 'inherited_insert_only_hunk' and any(line in new_lines for line in e['formatted_added_lines']):
            e['classification'] = 'new_formatting_relocation_destination'
    previous_file = REVIEW / 'engine-format-hunk-audit.json'
    previous = json.loads(previous_file.read_bytes())
    old_inherited = {(x['file'], tuple(x['input_hunk_lines'])) for x in previous['hunks'] if x['classification'].startswith('inherited')}
    return {'input': file.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'hunk_count': len(results), 'files': len({x['file'] for x in results}), 'classification_counts': dict(collections.Counter(x['classification'] for x in results)), 'previous_audit': {'path': previous_file.relative_to(ROOT).as_posix(), 'sha256': sha(previous_file.read_bytes()), 'previous_summary': previous['summary'], 'current_hunks_absent_from_previous_inherited': [{'file': x['file'], 'reported_line': x['reported_line']} for x in results if (x['file'], tuple(x['input_hunk_lines'])) not in old_inherited]}, 'hunks': results}


def corpus_audit():
    files = [ROOT / 'outputs/multi-stack/corpus-lint-1.log', ROOT / 'outputs/multi-stack/corpus-lint-2.log']
    reports = []
    for file in files:
        raw = file.read_bytes()
        rows = [{'file': m.group(1), 'line': int(m.group(2)), 'code': m.group(3), 'message': m.group(4)} for m in re.finditer(r'^([^\r\n]+\.md):(\d+): \[([^]]+)\] (.+)\r?$', raw.decode('utf-8-sig'), re.M)]
        reports.append({'input': file.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'diagnostics': rows, 'count': len(rows)})
    files = []
    for path in sorted({x['file'] for x in reports[-1]['diagnostics']}):
        src = source(path)
        files.append({'file': path, 'baseline_sha256': sha(src['baseline_bytes']), 'current_sha256': sha(src['current_bytes']), 'raw_bytes_identical_to_remote_main': src['baseline_bytes'] == src['current_bytes'], 'newline_normalized_sha256': sha(src['current_bytes'].replace(b'\r\n', b'\n')), 'byte_identical_after_only_crlf_to_lf': src['baseline_bytes'] == src['current_bytes'].replace(b'\r\n', b'\n'), 'baseline_crlf_count': src['baseline_bytes'].count(b'\r\n'), 'current_crlf_count': src['current_bytes'].count(b'\r\n'), 'bytes': len(src['current_bytes']), 'diagnostics': sum(x['file'] == path for x in reports[-1]['diagnostics'])})
    return {'logs': reports, 'remaining_diagnostics': reports[-1]['count'], 'unique_source_files': len(files), 'source_files': files}


result = {'baseline': BASE, 'remote_tracking_ref': 'origin/main', 'scope': 'Read-only source evidence for already scheduled checks, not a baseline rebuild or strict-check pass.', 'lint': lint_audit(), 'format': format_audit(), 'corpus': corpus_audit()}
OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'baseline': BASE, 'lint': {k: result['lint'][k] for k in ['compiler_message_records', 'unique_diagnostics', 'duplicate_records', 'levels', 'classification_counts', 'by_source_group', 'build_finished', 'previous_audit']}, 'format': {k: result['format'][k] for k in ['hunk_count', 'files', 'classification_counts', 'previous_audit']}, 'corpus': {k: result['corpus'][k] for k in ['remaining_diagnostics', 'unique_source_files', 'source_files']}}, indent=2))
