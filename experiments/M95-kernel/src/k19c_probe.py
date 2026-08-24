import sys

lines = int(sys.argv[1])
code = int(sys.argv[2])
for i in range(lines):
    print(f"Error: line {i}")
sys.exit(code)
