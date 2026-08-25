import re,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
t=open("docs/research/V-FOLD-audit.md",encoding="utf-8").read()
sec=t.split("## 8. Exact replacement text")[1].split("## 9.")[0]
lines=sec.split("\n")
n=0
for l in lines:
    s=l.strip()
    if s.startswith("`**") or s.startswith("` **["):
        n+=1
        bad=[i for i,ch in enumerate(s) if ch=="|" and (i==0 or s[i-1]!="\\")]
        print("repl %d: len=%d  unescaped_pipes=%d  single_line=%s" % (n,len(s),len(bad), "\n" not in s))
        if bad: print("    !! at",bad[:5], s[max(0,bad[0]-40):bad[0]+40])
print("total replacement lines:",n)
print()
print("=== V-FOLD attribution present in each?")
for l in lines:
    s=l.strip()
    if s.startswith("`**") or s.startswith("` **["):
        print("  ", "V-FOLD" in s, s[:70].replace("\n"," "))
