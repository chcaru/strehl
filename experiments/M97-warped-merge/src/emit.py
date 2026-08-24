import sys
import time

# Emit N lines then exit with a given code. Used to keep a native process alive
# long enough that a downstream `Select-Object -First` can cut the pipeline
# short before the process is reaped.
n = int(sys.argv[1])
code = int(sys.argv[2])
for i in range(n):
    print(f"line {i} Error marker")
    if i % 2000 == 0:
        sys.stdout.flush()
        time.sleep(0.01)
sys.stdout.flush()
sys.exit(code)
