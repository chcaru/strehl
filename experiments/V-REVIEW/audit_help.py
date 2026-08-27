import subprocess, pathlib
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
D = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\help"); D.mkdir(parents=True, exist_ok=True)
for name, args in [("root",["--help"]),("stack",["stack","--help"]),("align",["align","--help"]),
                   ("probe",["probe","--help"]),("version",["--version"])]:
    p = subprocess.run([EXE]+args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (D/(name+".txt")).write_bytes(p.stdout)
    print("%-8s rc=%d  %d bytes" % (name, p.returncode, len(p.stdout)))
# what subcommands actually exist
print()
print((D/"root.txt").read_text("utf8",errors="replace"))
