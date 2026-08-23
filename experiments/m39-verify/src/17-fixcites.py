import io
p = r'C:\dev\blog\death-of-software\projects\strehl\docs\research\M39-verify-detail-metric.md'
t = io.open(p, encoding='utf-8').read()
subs = [
 ('crates/strehl-cli/src/merge_cmd.rs:257-296',
  'crates/strehl-cli/src/merge_cmd.rs:276-310 (working tree, SHA-256 178B7E97..., verified stable during the run)'),
 ('all six `detail_metrics` tests\n   pass uniform sigma',
  'all seven `detail_metrics` tests\n   pass uniform sigma (`merge_cmd.rs:1537, 1579, 1600, 1631, 1676, 1696, 1697`)'),
 ('there are six `detail_metrics` tests', 'there are seven `detail_metrics` tests'),
 ('six `detail_metrics` tests', 'seven `detail_metrics` tests'),
]
for a, b in subs:
    if a in t:
        t = t.replace(a, b); print('applied:', a[:60])
    else:
        print('NOT FOUND:', a[:60])
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
