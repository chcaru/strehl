import subprocess
import sys


def main() -> None:
    root = r"C:\dev\blog\death-of-software\projects\strehl"
    blob = subprocess.run(
        ["git", "show", "701dc11:docs/research/M60-bimodality.md"],
        cwd=root, capture_output=True,
    ).stdout.decode("utf-8")
    with open(root + r"\docs\research\M60-bimodality.md", encoding="utf-8") as fh:
        work = fh.read()
    a = blob.replace("\r\n", "\n").strip()
    b = work.replace("\r\n", "\n").strip()
    print("committed chars:", len(a), " worktree chars:", len(b))
    print("identical:", a == b)
    for s in ["+0.772", "14.52", "782\u20131124", "24-numden.py", "**P16**",
              "9.4 The law's prediction", "five independent measurements"]:
        print(f"  {str(s in a):5s}  {s}")
    sys.exit(0 if a == b else 1)


if __name__ == "__main__":
    main()
