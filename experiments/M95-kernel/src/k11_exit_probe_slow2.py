import sys, time
code = int(sys.argv[1])
for i in range(10):
    print(f"Error: line {i}", flush=True)
    time.sleep(0.6)
sys.exit(code)
