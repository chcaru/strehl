"""V-KILLB0 softverdict.py -- verdict-binding check for the SOFT GATE finding.

Derives the conclusion MECHANICALLY from the measured numbers. A presence test
("does the word 'inert' appear") cannot detect a reversed conclusion, so every
check below is pinned to the specific claim it certifies, and the harness is
commissioned with mutations that flip the CONCLUSION, not merely a number.
"""
import sys, copy

# --- measured facts, as recorded by softlive.py / softlive2.py and the runs ---
M = dict(
    typo_exit_pyramid_coffee = 0,     # STREHL_SOFT_GATE=gausian, default backend
    typo_exit_pyramid_bee    = 0,     # same, bee-1-cpl --srgb
    typo_exit_estimator      = 101,   # same typo, --merge estimator -> panic
    valid_exit_estimator     = 0,     # gaussian, --merge estimator -> ok
    ndiff_pyr_112            = 0,     # gaussian vs unset, pyramid, 112MSDCF
    ndiff_pyr_bee            = 0,     # exponential vs unset, pyramid, bee srgb
    ndiff_est_112            = 14626891,
    ndiff_est_expo           = 22109494,
    samples_pyr_bee          = 98898048,
    comparator_planted       = 1,     # planted 1-sample defect -> must read 1
    comparator_null          = 0,     # array vs itself -> must read 0
)

def derive(m):
    """Return (verdict, reasons). Pure function of the measurements."""
    r = []
    # C1: the comparator must be alive, else every n_diff below is meaningless.
    if m['comparator_planted'] != 1 or m['comparator_null'] != 0:
        return "VOID", ["comparator failed commissioning; no pixel claim is readable"]
    r.append("comparator commissioned: planted=1, null=0")
    # C2: the env var must be readable by this binary at all, else 'inert'
    #     would be indistinguishable from 'not compiled in'.
    if m['typo_exit_estimator'] == 0:
        return "VOID", ["typo did not fail on ANY path; switch may not exist in build"]
    if m['valid_exit_estimator'] != 0:
        return "VOID", ["valid kernel failed; probe is not specific to the typo"]
    r.append("switch proven readable: typo->%d, valid->%d on estimator"
             % (m['typo_exit_estimator'], m['valid_exit_estimator']))
    # C3: live-or-inert on the SHIPPING default path.
    pyr_silent = (m['typo_exit_pyramid_coffee'] == 0 and m['typo_exit_pyramid_bee'] == 0)
    pyr_nopix  = (m['ndiff_pyr_112'] == 0 and m['ndiff_pyr_bee'] == 0)
    est_pix    = (m['ndiff_est_112'] > 0)
    if pyr_silent and pyr_nopix and est_pix:
        r.append("pyramid: typo silent AND 0 pixels moved; estimator: %d pixels moved"
                 % m['ndiff_est_112'])
        return "INERT_ON_SHIPPING_DEFAULT", r
    if not pyr_nopix:
        return "LIVE_ON_SHIPPING_DEFAULT", r + ["pyramid moved pixels"]
    return "INDETERMINATE", r

def scorable(verdict):
    """Is ORCH's STEP TWO (default/gaussian/exponential, same everything else)
    constructible?  Only if the kernel is live on the same merge as the baseline."""
    return verdict == "LIVE_ON_SHIPPING_DEFAULT"

v, reasons = derive(M)
print("DERIVED VERDICT: %s" % v)
for x in reasons: print("   - " + x)
print("STEP-TWO CONSTRUCTIBLE AS SPECIFIED: %s" % scorable(v))
print()

# ---- commissioning: mutations that FLIP THE CONCLUSION must all be caught ----
ARMS = [
    ("pyramid actually moved pixels",      dict(ndiff_pyr_112=5, ndiff_pyr_bee=5), "LIVE_ON_SHIPPING_DEFAULT"),
    ("typo failed loudly on pyramid too",  dict(typo_exit_pyramid_bee=101),        "INDETERMINATE"),
    ("switch not readable anywhere",       dict(typo_exit_estimator=0),            "VOID"),
    ("estimator moved nothing either",     dict(ndiff_est_112=0),                  "INDETERMINATE"),
    ("comparator dead (null broken)",      dict(comparator_null=7),                "VOID"),
    ("comparator dead (blind to defect)",  dict(comparator_planted=0),             "VOID"),
    ("valid kernel also errored",          dict(valid_exit_estimator=101),         "VOID"),
]
# --- ARM-SET PIN (added after softaudit.py caught this exact hole) ---
# Without this, DELETING an arm keeps `caught == len(ARMS)` and the check stays
# green: the harness would certify itself on a shrunken commissioning set.
# The count AND the names are pinned, so neither deletion nor substitution passes.
EXPECTED_ARM_NAMES = frozenset({
    "pyramid actually moved pixels", "typo failed loudly on pyramid too",
    "switch not readable anywhere", "estimator moved nothing either",
    "comparator dead (null broken)", "comparator dead (blind to defect)",
    "valid kernel also errored",
})
_names = {a[0] for a in ARMS}
if len(ARMS) != 7 or _names != EXPECTED_ARM_NAMES:
    sys.exit("FATAL: commissioning arm set altered. missing=%s unexpected=%s n=%d"
             % (sorted(EXPECTED_ARM_NAMES - _names), sorted(_names - EXPECTED_ARM_NAMES), len(ARMS)))

caught = 0
for name, patch, expect in ARMS:
    m2 = copy.deepcopy(M); m2.update(patch)
    v2, _ = derive(m2)
    ok = (v2 != v) and (v2 == expect)
    caught += ok
    print("  %-38s -> %-28s %s" % (name, v2, "CAUGHT" if ok else "*** MISSED ***"))
print()
print("conclusion-flip arms caught: %d/%d" % (caught, len(ARMS)))
if caught != len(ARMS):
    sys.exit("FATAL: harness cannot detect a reversed conclusion")
print("BINDING CHECK PASSED -- the verdict above is pinned to the measurements, not asserted.")

