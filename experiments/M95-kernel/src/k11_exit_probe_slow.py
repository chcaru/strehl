import sys
import time

for i in range(10):
    print(f"Error: line {i}", flush=True)
    time.sleep(0.6)
sys.exit(1)
