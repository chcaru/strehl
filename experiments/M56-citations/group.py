import io, json, collections
rows = json.load(io.open('experiments/M56-citations/cites.json', encoding='utf-8'))
g = collections.defaultdict(list)
for c in rows:
    g[(int(c['num']), c['file'])].append(c['line'])
by_fact = collections.defaultdict(list)
for (n, f), lines in g.items():
    by_fact[n].append((f, sorted(set(lines))))
print('distinct facts:', len(by_fact), ' instances:', len(rows))
for n in sorted(by_fact):
    for f, lines in sorted(by_fact[n]):
        ls = ', '.join(str(x) for x in lines[:9]) + ('...' if len(lines) > 9 else '')
        print(f'{n}|{f.replace("crates/","")}|{ls}')
