"""Do the three .commitmsg dangling blobs correspond to commits that ACTUALLY
landed?  A drafted message with no matching commit is the -First masking failure
mode in the wild: the agent wrote the message, the commit silently failed, and
the loop printed nothing.
"""
import subprocess

def run(a):
    p = subprocess.run(a, capture_output=True, text=True, errors="replace")
    return p.stdout

blobs = [l.split()[2] for l in run(["git","fsck","--dangling","--no-progress"]).splitlines()
         if l.startswith("dangling blob")]
subjects = run(["git","log","--all","--format=%H%x09%s"]).splitlines()
print("dangling blobs: %d   commits in --all: %d\n" % (len(blobs), len(subjects)))

for b in blobs:
    content = run(["git","cat-file","-p",b])
    first = content.splitlines()[0].strip() if content.strip() else ""
    body = content.splitlines()
    buildish = sum(1 for l in body[:40]
                   if l.strip().startswith(("Compiling", "Finished", "Downloaded",
                                            "warning:", "Updating")))
    if buildish >= 3:
        print("blob %s\n   -> BUILD LOG (%d cargo lines) - not a commit message\n"
              % (b[:10], buildish))
        continue
    if not first or len(first) > 200 or first.startswith(("//", "#", "==")):
        continue                      # not a commit message
    hit = [s for s in subjects if s.split("\t",1)[-1].strip() == first]
    print("blob %s" % b[:10])
    print("   subject : %s" % first[:88])
    if hit:
        h = hit[0].split("\t")[0]
        anc = subprocess.run(["git","merge-base","--is-ancestor",h,"HEAD"],
                             capture_output=True).returncode == 0
        print("   -> LANDED as %s   ancestor-of-HEAD=%s" % (h[:10], anc))
    else:
        print("   -> *** NO COMMIT WITH THIS SUBJECT -- message drafted, commit never landed ***")
    print()

