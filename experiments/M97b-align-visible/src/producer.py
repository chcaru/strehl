import sys, time

n = int(sys.argv[1])
delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
for i in range(n):
    print("LINE%d" % i)
    if delay:
        sys.stdout.flush()
        time.sleep(delay)
sys.exit(1)
