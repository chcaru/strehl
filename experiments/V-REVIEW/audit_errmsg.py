import subprocess
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
p = subprocess.run([EXE,"stack",DIR,"--merge","bogus"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print("rc=%d" % p.returncode)
print(p.stdout.decode("utf8","replace"))
