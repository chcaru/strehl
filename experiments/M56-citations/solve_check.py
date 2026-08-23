import math

def solve(ladder, target):
    v = sorted(ladder)
    lo, hi = v[0], v[-1]
    if target < lo[1]:
        return ('BelowLadder', lo[0], lo[1])
    if target > hi[1]:
        return ('AboveLadder', hi[0], hi[1])
    for (g0, n0), (g1, n1) in zip(v, v[1:]):
        if n0 <= target <= n1:
            f = (math.log(target) - math.log(n0)) / (math.log(n1) - math.log(n0))
            return ('Gate', math.exp(math.log(g0) + f * (math.log(g1) - math.log(g0))))
    return ('Unusable',)

FROZEN = {
    '119MSDCF': [(0.5,1.275),(1.0,1.581),(2.0,2.258),(4.0,3.654)],
    '109MSDCF': [(0.5,1.414),(1.0,1.884),(2.0,2.891),(4.0,4.987)],
    '113MSDCF': [(0.5,1.433),(1.0,2.198),(2.0,4.774),(4.0,8.590)],
    '112MSDCF': [(0.5,1.554),(1.0,2.572),(2.0,6.226),(4.0,12.065)],
    'coffee-bean': [(0.5,1.516),(1.0,2.570),(2.0,7.422),(4.0,24.700)],
}
# measured by me today, HEAD 90e7db5 binary
TODAY = {
    '119MSDCF': [(0.5,1.399),(1.0,1.855),(2.0,2.847),(4.0,4.723)],
    '109MSDCF': [(0.5,1.414),(1.0,1.884),(2.0,2.891),(4.0,4.987)],
    '113MSDCF': [(0.5,1.432),(1.0,2.194),(2.0,4.761),(4.0,8.581)],
    '112MSDCF': [(0.5,1.551),(1.0,2.561),(2.0,6.190),(4.0,12.037)],
    'coffee-bean': [(0.5,1.870),(1.0,4.072),(2.0,14.386),(4.0,31.614)],
    'coffee-bubbles': [(0.5,1.238),(1.0,1.504),(2.0,2.109),(4.0,3.529)],
    'foam': [(0.5,1.043),(1.0,1.087),(2.0,1.177),(4.0,1.359)],
}

def report(name, d, keys):
    gates = []
    print('###', name)
    for k in keys:
        r = solve(d[k], 3.0)
        print(f'  {k:16s} {r}')
        if r[0] == 'Gate':
            gates.append(r[1])
    lo, hi = min(gates), max(gates)
    print(f'  lo={lo:.4f} hi={hi:.4f} ratio={hi/lo:.4f}')
    print(f'  assert (1.0..1.2).contains(lo) -> {1.0 <= lo < 1.2}')
    print(f'  assert (2.7..3.1).contains(hi) -> {2.7 <= hi < 3.1}')
    print(f'  assert hi/lo > 2.4           -> {hi/lo > 2.4}')
    print()

five = ['119MSDCF','109MSDCF','113MSDCF','112MSDCF','coffee-bean']
report('FROZEN LADDERS (what the green test actually asserts on)', FROZEN, five)
report('TODAY, same five stacks', TODAY, five)
report('TODAY, all seven stacks', TODAY, list(TODAY))
# per-rung staleness
print('### per-rung drift frozen -> today (same five)')
for k in five:
    for (g, nf), (_, nt) in zip(FROZEN[k], TODAY[k]):
        print(f'  {k:12s} gate {g:4.1f}: frozen {nf:8.3f}  today {nt:8.3f}  {100*(nt/nf-1):+7.2f}%')
