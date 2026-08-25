import json, datetime as dt
rows = json.load(open(r"C:\dev\strehl-out\M117\corpus.json"))
WIN_OPEN  = dt.datetime.fromisoformat("2026-08-24 03:15:23-07:00")
WIN_SHUT  = dt.datetime.fromisoformat("2026-08-24 13:41:53-07:00")
def pd(s):
    parts = s.split(None,1)
    if len(parts)<2: return None
    return dt.datetime.fromisoformat(parts[1].strip())

pre=post=inwin=0
inwin_rows=[]
for r in rows:
    a = pd(r["added"]); l = pd(r["last"])
    if a is None: r["cls"]="NODATE"; continue
    if l is not None and l < WIN_OPEN:
        r["cls"]="IMMUNE-PRE"; pre+=1
    elif a > WIN_SHUT:
        r["cls"]="IMMUNE-POST"; post+=1
    else:
        r["cls"]="IN-WINDOW"; inwin+=1; inwin_rows.append(r)
print(f"total={len(rows)}  IMMUNE-PRE(landed before window opened)={pre}  IMMUNE-POST(first landed after fix)={post}  IN-WINDOW={inwin}")
print()
print(f"{'report':46s} {'added':22s} {'last':22s} algn0 algnEnv wmap cdir alignCmd --ref smooth")
for r in sorted(inwin_rows, key=lambda x: x["added"].split(None,1)[1]):
    print(f"{r['file'][:46]:46s} {r['added'].split(None,1)[1][:19]:22s} {r['last'].split(None,1)[1][:19]:22s} "
          f"{r['align0']:5d} {r['align_env']:7d} {r['warpmap']:4d} {r['cachedir']:4d} {r['align_cmd']:8d} {r['ref_flag']:5d} {r['smooth']:6d}")
json.dump(rows, open(r"C:\dev\strehl-out\M117\corpus_cls.json","w"), indent=1)
