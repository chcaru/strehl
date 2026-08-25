import re
t=open("docs/research/SYNTHESIS.md",encoding="utf-8").read()
c=re.sub(r"\s+"," ",t)
for pat in ["1.1975","2.2300","0.4530","1.4890","1.489","1.6361","0.4486","10.4 %","20.3 %","27.4","7.7 %"]:
    idxs=[m.start() for m in re.finditer(re.escape(pat), c)]
    print(f"--- {pat}: {len(idxs)} hits")
    for i in idxs[:4]:
        print("   ...", c[max(0,i-160):i+120].replace("\n"," "))
