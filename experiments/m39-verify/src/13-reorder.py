import io
p = r'C:\dev\blog\death-of-software\projects\strehl\docs\research\M39-verify-detail-metric.md'
lines = io.open(p, encoding='utf-8').read().split('\n')
# 1-based line numbers from Select-String -> 0-based indices
head = lines[0:9]          # lines 1..9  (header, before line 10)
s1   = lines[9:85]         # 10..85   (S1, up to the --- separator block before 86)
s3   = lines[85:181]       # 86..181  (S3)
s2   = lines[181:293]      # 182..293 (S2)
rest = lines[293:]         # 294..end (S4 onward)
out = head + s1 + s2 + s3 + rest
io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
print('sections now:')
for i, l in enumerate(out, 1):
    if l.startswith('## '):
        print(i, l)
