import json, collections
d = json.load(open(r"D:\strehl-out\V-REVIEW\halo\trunc2.json"))
print("subjects:", len(d))
print("verdicts:", dict(collections.Counter(v["verdict"] for v in d.values())))
print("keys of one:", sorted(next(iter(d.values())).keys()))
FLAG = ("flat-on-ruler-cpl","tweezers-cpl","lavendar-cpl","119MSDCF")
full = [k for k,v in d.items() if v["verdict"]!="UNMEASURABLE" and v.get("used",0)==7]
print("full 7-band walks:", len(full))
print("  of which flagged:", [k for k in full if k in FLAG])
print("  clean full walk :", len([k for k in full if k not in FLAG]))
blind = [k for k,v in d.items() if v["verdict"]!="UNMEASURABLE" and v.get("used",0)<7]
print("blind:", len(blind), sorted(blind))
unm = [k for k,v in d.items() if v["verdict"]=="UNMEASURABLE"]
print("unmeasurable:", len(unm))
print("SUM:", len([k for k in full if k not in FLAG]) + len([k for k in full if k in FLAG]) + len(blind) + len(unm))
