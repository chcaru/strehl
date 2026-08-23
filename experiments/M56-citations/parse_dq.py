import io, re, json
L = io.open('docs/research/SYNTHESIS.md', encoding='utf-8').read().split('\n')
def block(a, b):
    return L[a-1:b-1]
# disciplines: section 5 (1268..2164); questions: section 10 (2525..end)
def numbered(lines, start_lineno):
    out = {}
    cur = None
    for i, ln in enumerate(lines):
        m = re.match(r'^\s*(\d+)\.\s+(.*)$', ln)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {'line': start_lineno + i, 'text': m.group(2)})
        elif cur is not None and ln.strip():
            out[cur]['text'] += ' ' + ln.strip()
        elif not ln.strip():
            cur = None
    return out
disc = numbered(block(1268, 2164), 1268)
ques = numbered(block(2525, len(L)+1), 2525)
json.dump({'disc': disc, 'ques': ques}, io.open('experiments/M56-citations/disc_ques.json','w',encoding='utf-8'))
print('disciplines parsed:', len(disc), 'max', max(int(k) for k in disc))
print('questions parsed:', len(ques), 'max', max(int(k) for k in ques))
for n in ['210','29','120','291','288','257','264','303','3','15','35']:
    d = disc.get(n)
    print('---- DISC', n, '::', (d['text'][:300] if d else 'MISSING'))
for n in ['90','17','129','147','100','102']:
    q = ques.get(n)
    print('==== Q', n, '::', (q['text'][:300] if q else 'MISSING'))
