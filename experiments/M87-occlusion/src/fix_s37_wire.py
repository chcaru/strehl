"""M87 / s37 -- wires P155-P157 into verify_s34 and control_s34.

Two ordering lessons from s36 are encoded as hard preconditions here rather
than as care:

  1. control_s34.JSONS is the backup list. An arm mutating a file absent from
     it prints "RED ok" and never restores. So the new JSONs are appended
     FIRST and their presence is asserted before any arm is written.
  2. arm() only appends to a list; the loop that consumes it sits lower in
     the file. Arms inserted below that loop register into an already-
     iterated list, never run, and the suite reports a clean pass. So the
     insertion is anchored on the LOOP and the arms go ABOVE it, and the
     script prints the arm count the caller must then verify.

Every check re-derives from data/113-rankphase.json and
data/114-phaseperiod.json. None reads a value back out of the prose.
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent
V = SRC / "verify_s34.py"
C = SRC / "control_s34.py"

V_ANCHOR = '    print(f"\\nverify_s34: {checks[0]} checks, {len(fails)} failures")'

V_BLOCK = '''
    # ---- P155-P157: the rank retraction and the phase law -----------------
    rp = json.loads((DATA / "113-rankphase.json").read_text(encoding="utf-8"))
    pp = json.loads((DATA / "114-phaseperiod.json").read_text(encoding="utf-8"))
    p155 = next(l for l in raw.split("\\r\\n") if l.startswith("| P155 |"))
    p156 = next(l for l in raw.split("\\r\\n") if l.startswith("| P156 |"))
    p157 = next(l for l in raw.split("\\r\\n") if l.startswith("| P157 |"))
    g = {r["sep_quanta"]: r for r in pp["grid"]}

    ck(rp["T1"]["mismatches"] == 0,
       "P155: median commutes with the quantiser, 0 mismatches")
    ck("**0** mismatches" in p155, "P155 states the mismatch count")
    ck("retract" in p155.lower(), "P155 actually retracts, not merely qualifies")
    ck(f"**{rp['T2']['max_abs_e']:.4f} DN**" in p155,
       "P155 quotes the measured sawtooth amplitude")
    ck(rp["T2"]["max_abs_e"] <= rp["T2"]["half_delta"] + 1e-9,
       "P155: the amplitude really is bounded by half a quantum")

    ck(rp["T3"]["pass"] is False,
       "P156: the decay prediction is recorded as FAILED")
    ck("failed" in p156.lower(), "P156 says its own prediction failed")
    ck(pp["T5"]["pass"] and pp["T6"]["pass"],
       "P156: both registered periodicity arms passed")
    ck(g[0.5]["rho_median"] < -0.20 and g[1.5]["rho_median"] < -0.20
       and g[2.5]["rho_median"] < -0.20,
       "P156: all three half-integer separations are antiphase")
    ck(g[1.0]["rho_median"] > 0.60 and g[2.0]["rho_median"] > 0.60
       and g[3.0]["rho_median"] > 0.60,
       "P156: all three integer separations restore phase")
    ck(f"**+{g[2.0]['rho_median']:.4f}**" in p156,
       "P156 quotes the 2-quanta correlation from the artefact")

    ck(abs(pp["T7"]["rho"]) < 0.25, "P157: the phase-blind bin really reads ~0")
    ck(f"**+{pp['T7']['rho']:.4f}**" in p157,
       "P157 quotes the phase-blind correlation")
    ck(pp["T8"]["pass"] is True,
       "P157: the mean shows the same periodicity, killing the discriminator")
    ck(abs(g[1.5]["rho_mean"]) > abs(g[1.5]["rho_median"]),
       "P157: the mean's antiphase correlation is STRONGER, not weaker")
    ck(pp["discriminator_rank_vs_mean_survives"] is False,
       "P157: the rank-vs-mean discriminator is recorded as dead")
    ck(p157.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() == "ARGUED",
       "P157's STATUS CELL is ARGUED -- it is a test, not a finding")
    ck(p155.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() == "MEASURED",
       "P155's STATUS CELL is MEASURED")
    ck(p156.rstrip().rstrip("|").rsplit("|", 1)[-1].strip() == "MEASURED",
       "P156's STATUS CELL is MEASURED")

'''

LOOP = "    for tag, why, expect, fn, want in arms:"

ARMS = '''    arm("N53", "the commuting result is broken, which would resurrect the "
        "rank framing P155 exists to retract", "RED",
        lambda: mutate_json("113-rankphase.json", ["T1", "mismatches"], 47),
        want="median commutes with the quantiser, 0 mismatches")
    arm("N54", "the sawtooth amplitude is pushed above half a quantum, "
        "breaking the bound P155 rests on", "RED",
        lambda: mutate_json("113-rankphase.json", ["T2", "max_abs_e"], 41.9),
        want="the amplitude really is bounded by half a quantum")
    arm("N55", "my failed decay prediction is quietly recorded as having "
        "passed", "RED",
        lambda: mutate_json("113-rankphase.json", ["T3", "pass"], True),
        want="the decay prediction is recorded as FAILED")
    arm("N56", "one half-integer separation is flipped positive, destroying "
        "the antiphase half of the periodicity claim", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["grid", 6, "rho_median"],
                            0.31),
        want="all three half-integer separations are antiphase")
    arm("N57", "the phase-blind correlation is inflated, removing the "
        "result that speaks to a failed prediction elsewhere", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["T7", "rho"], 0.77),
        want="the phase-blind bin really reads ~0")
    arm("N58", "the mean is made to behave differently from the median, "
        "reviving the discriminator P157 kills", "RED",
        lambda: mutate_json("114-phaseperiod.json", ["T8", "pass"], False),
        want="the mean shows the same periodicity, killing the discriminator")

'''

JS_OLD = '         "provenance-74.json", "launder-direction.json"]'
JS_NEW = ('         "provenance-74.json", "launder-direction.json",\n'
          '         "113-rankphase.json", "114-phaseperiod.json"]')


def main():
    c = C.read_text(encoding="utf-8")
    if c.count(JS_OLD) != 1:
        sys.exit("JSONS ANCHOR NOT UNIQUE (%d)" % c.count(JS_OLD))
    if "N53" in c:
        sys.exit("already wired -- refusing to double-insert")
    c = c.replace(JS_OLD, JS_NEW, 1)
    for name in ("113-rankphase.json", "114-phaseperiod.json"):
        if name not in c:
            sys.exit("%s NOT REGISTERED -- arms would not restore" % name)
    if c.count(LOOP) != 1:
        sys.exit("LOOP ANCHOR NOT UNIQUE (%d)" % c.count(LOOP))
    c = c.replace(LOOP, ARMS + LOOP, 1)
    if c.index('arm("N53"') > c.index(LOOP):
        sys.exit("ARMS LANDED BELOW THE LOOP -- they would never run")
    C.write_text(c, encoding="utf-8")
    print("control_s34.py: JSONs registered, arms N53-N58 inserted ABOVE the loop")

    v = V.read_text(encoding="utf-8")
    if v.count(V_ANCHOR) != 1:
        sys.exit("VERIFIER ANCHOR NOT UNIQUE (%d)" % v.count(V_ANCHOR))
    if "P155-P157" in v:
        sys.exit("verifier already wired")
    V.write_text(v.replace(V_ANCHOR, V_BLOCK + V_ANCHOR, 1), encoding="utf-8")
    print("verify_s34.py: P155-P157 block inserted")
    print("REQUIRE '58 arms' on the next control_s34 run -- the count, not "
          "the pass, is what detects a mis-anchored arm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
