"""Commission vn_verify8.py: plant defects in section 8 and require RED.

A green checker on its first real run is a claim about the checker, not about
the document. Each plant below is anchored on a string whose occurrence count is
verified to be exactly 1 before it is used, and a plant that does not land is a
hard error -- not a silent pass.

Three arms, because a two-arm commissioning cannot tell a working checker from
one that dies:
  PLANT   -- a defect must produce rc=1 (FAILED)
  PLACEBO -- a no-op edit must produce rc=0
  CRASH   -- a broken checker must produce rc=2 (REFUSED), never 0 or 1
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
CHK = os.path.join(HERE, "vn_verify8.py")
BAK = os.path.join(os.environ["TEMP"], "vn_negctl8_RESULT.md")
CBAK = os.path.join(os.environ["TEMP"], "vn_negctl8_verify8.py")

PLANTS = [
    ("| excess vs mixedness `4p(1-p)` | **+0.174** | 0.41 |",
     "| excess vs mixedness `4p(1-p)` | **+0.274** | 0.41 |", "rho_mix digit"),
    ("| excess vs mixedness `4p(1-p)` | **+0.174** | 0.41 |",
     "| excess vs mixedness `4p(1-p)` | **+0.174** | 0.61 |", "p_mix digit"),
    ("| excess vs raw averaged fraction | **+0.174** | 0.41 |",
     "| excess vs raw averaged fraction | **+0.170** | 0.41 |", "rho_raw"),
    ("| the 26 masters' provenance | `STREHL_SOFT_GATE = (unset)` on **26 of 26** |",
     "| the 26 masters' provenance | `STREHL_SOFT_GATE = (unset)` on **25 of 26** |",
     "soft-gate census"),
    ("| `109MSDCF` | **0.997** — the most mixed in the corpus | **0.996** | no excess at all |",
     "| `109MSDCF` | **0.897** — the most mixed in the corpus | **0.996** | no excess at all |",
     "109MSDCF mixedness"),
    ("| `bee-2-cpl` | 0.086 | **1.948** — the worst in the corpus | nearly unmixed |",
     "| `bee-2-cpl` | 0.086 | **1.848** — the worst in the corpus | nearly unmixed |",
     "bee-2-cpl excess"),
    ("`softgate.rs` differs by **29 lines**",
     "`softgate.rs` differs by **31 lines**", "softgate drift"),
    ("`merge.rs` by 142 and `focus.rs` by 630", 
     "`merge.rs` by 148 and `focus.rs` by 630", "merge.rs drift"),
    ("`merge.rs` by 142 and `focus.rs` by 630",
     "`merge.rs` by 142 and `focus.rs` by 631", "focus.rs drift"),
    ("> response rises out of the noise floor, because the gate's tolerance is an",
     "> response falls below the noise floor, because the gate's tolerance is an",
     "M111 quote fidelity"),
    ("The tolerance is fixed at `4.0 * sqrt(2) * FOCUS_NOISE_SD` = **0.086063**",
     "The tolerance is fixed at `4.0 * sqrt(2) * FOCUS_NOISE_SD` = **0.086073**",
     "tolerance constant"),
    ("Admission falls **285 to 1** while the response rises about 8x.",
     "Admission falls markedly while the response rises about 8x.",
     "n_eff collapse"),
    ("Partition: 26 examined = **24 measured + 2 refused + 0 failed**.",
     "Partition: 26 examined = **23 measured + 2 refused + 0 failed**.",
     "partition sum"),
]

PLACEBO = ("Reporting the refutation first, as instructed.",
           "Reporting the refutation first, as ORCH instructed.")


def run():
    p = subprocess.run([sys.executable, CHK], capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def apply(old, new, label):
    t = io.open(DOC, encoding="utf-8").read()
    n = t.count(old)
    if n != 1:
        raise SystemExit("PLANT ANCHOR NOT UNIQUE (%s): %r occurs %d times"
                         % (label, old[:60], n))
    io.open(DOC, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))


def restore(src, dst):
    shutil.copyfile(src, dst)


def main():
    shutil.copyfile(DOC, BAK)
    shutil.copyfile(CHK, CBAK)
    caught = missed = 0
    crashes = 0
    try:
        rc, out = run()
        if rc != 0:
            raise SystemExit("baseline is not green (rc=%d):\n%s" % (rc, out))
        print("baseline GREEN")

        for old, new, label in PLANTS:
            apply(old, new, label)
            rc, out = run()
            restore(BAK, DOC)
            if rc == 2:
                crashes += 1
                print("  CRASH   %-22s (a crash is not a catch)" % label)
            elif rc == 1:
                caught += 1
                print("  caught  %s" % label)
            else:
                missed += 1
                print("  MISSED  %-22s rc=%d" % (label, rc))

        apply(PLACEBO[0], PLACEBO[1], "placebo")
        rc, out = run()
        restore(BAK, DOC)
        placebo_ok = (rc == 0)
        print("  placebo %s (rc=%d)" % ("clean" if placebo_ok else "DIRTY", rc))

        # CRASH ARM: break the checker and require rc=2, not 0 and not 1.
        t = io.open(CHK, encoding="utf-8").read()
        old = "    doc = io.open(DOC, encoding=\"utf-8\").read()"
        if t.count(old) != 1:
            raise SystemExit("crash-arm anchor not unique")
        io.open(CHK, "w", encoding="utf-8", newline="\n").write(
            t.replace(old, "    raise RuntimeError('planted crash')\n" + old))
        rc, out = run()
        restore(CBAK, CHK)
        crash_ok = (rc == 2 and "REFUSED" in out)
        print("  crash arm %s (rc=%d, expected 2)"
              % ("distinguishes refusal from pass" if crash_ok else "BROKEN", rc))
    finally:
        restore(BAK, DOC)
        restore(CBAK, CHK)

    same = (io.open(DOC, encoding="utf-8").read()
            == io.open(BAK, encoding="utf-8").read())
    print("\n%d/%d plants caught; placebo %s; %d crash(es); restore %s"
          % (caught, len(PLANTS), "clean" if placebo_ok else "DIRTY",
             crashes, "verified byte-identical" if same else "DIFFERS"))
    ok = (caught == len(PLANTS) and placebo_ok and crashes == 0
          and crash_ok and same)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
