"""M87 / s36 -- adds control arms N47-N52 for P152-P154.

Each arm mutates the artefact a P152-P154 check re-derives from and must turn
verify_s34 RED. An arm that stays GREEN means the check is decorative.

Both target JSONs were added to control_s34.JSONS by fix_s36_wire.py BEFORE
this ran. That ordering is the whole lesson from the last section: an arm
mutating a file absent from the backup list prints "RED ok" and never
restores, and only the terminal no-mutation arm notices.

Two arms are deliberately aimed at the checks that guard my OWN failures --
N50 flips Q2 back to passing and N51 erases the FAIL token -- because a
self-correction that no control defends is a sentence, not a result.
"""
import pathlib
import sys

C = pathlib.Path(__file__).resolve().parent / "control_s34.py"

ANCHOR = """    restore()
    colour, out = run()
    green = "N%d" % (len(results) + 1)"""

ARMS = '''    arm("N47", "the headline's source closure is made to touch the laundered "
        "array, which is the exact thing P152 denies", "RED",
        lambda: mutate_json("provenance-74.json", ["R2", "overlap"],
                            ["45-locate.py"]),
        want="headline source closure does not touch ship-delta.npy")
    arm("N48", "the luma level count is dropped to an 8-bit-reachable value, "
        "destroying P152's positive test", "RED",
        lambda: mutate_json("provenance-74.json",
                            ["R1", "arrays", "bee3-leg-luma.npy",
                             "levels_slice"], 231),
        want="the level count actually exceeds what 8 bits can hold")
    arm("N49", "the amplitude factor is moved off the 16-to-8 quantisation "
        "ratio, breaking P153's mechanism claim", "RED",
        lambda: mutate_json("provenance-74.json", ["R3", "factor"], 180.0),
        want="the factor really is the 16-to-8 quantisation ratio")
    arm("N50", "Q2 is flipped to passing, i.e. my failed prediction is "
        "quietly recorded as having succeeded", "RED",
        lambda: mutate_json("launder-direction.json", ["Q2", "pass"], True),
        want="Q2 is recorded as FAILED, not quietly dropped")
    arm("N51", "the merge is made to move toward zero like frame 0, removing "
        "the opposite-directions finding P154 rests on", "RED",
        lambda: mutate_json("launder-direction.json", ["Q2", "v_laundered"],
                            -5.9),
        want="the merge veil really did deepen under laundering")
    arm("N52", "the changed-fraction ratio is inflated, turning P153's "
        "retraction back into the overstatement it retracts", "RED",
        lambda: mutate_json("provenance-74.json", ["R4", "ratio"], 3.4),
        want="the fraction ratio is small, which is what makes it a retraction")

'''


def main():
    c = C.read_text(encoding="utf-8")
    if c.count(ANCHOR) != 1:
        sys.exit("ARM ANCHOR NOT UNIQUE (%d) -- refusing to guess" % c.count(ANCHOR))
    if "N47" in c:
        sys.exit("already wired -- refusing to double-insert")
    for name in ("provenance-74.json", "launder-direction.json"):
        if name not in c:
            sys.exit("%s IS NOT IN JSONS -- arms would mutate without restore"
                     % name)
    c = c.replace(ANCHOR, ARMS + ANCHOR, 1)
    C.write_text(c, encoding="utf-8")
    print("control_s34.py: arms N47-N52 inserted (backup registration verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
