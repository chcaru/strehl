import io
p = r'C:\dev\blog\death-of-software\projects\strehl\docs\research\M39-verify-detail-metric.md'
lines = io.open(p, encoding='utf-8').read().split('\n')
for i in range(0, 12):
    print(i, repr(lines[i]))
