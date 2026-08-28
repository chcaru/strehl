import io

body = """# SELF-AUDIT: my verifier could not see a reversed verdict

V-REVIEW, answering item 3 of ORCH's broadcast and the postscript to correction
#5. I ran the check on my own harness rather than assuming it was exempt.

## The defect, MEASURED in my own instrument

`vr_recheck.py` re-derives each adjudicated master's statistics and compares them
to a frozen baseline. It printed:

```
GREEN  all 2 adjudicated masters still read what report.md ruled on.
```

**It never opened `report.md`.** The claim names a file the checker does not
read. Commissioned with `vp_flipcommission.py`, six arms, every mutation anchored
on a unique full line and hard-erroring if it did not land:

| arm | expect | exit | result |
| --- | --- | --- | --- |
| NULL | GREEN | 0 | OK |
| FLIP-ROW `ACQUIT`->`CONVICT` | ? | 0 | **MISSED** |
| FLIP-HEAD `Nine ACQUIT, zero CONVICT` reversed | ? | 0 | **MISSED** |
| FLIP-NUM ratio `0.885`->`1.885` | ? | 0 | **MISSED** |
| POS-BASE baseline stat +10% | RED | 2 | CAUGHT |
| POS-DIR empty masters dir | RED | 2 | CAUGHT |

**3 of 3 conclusion flips missed; 2 of 2 planted defects caught.** The potency
arms matter: without them "missed" could have meant a dead harness. It was not
dead. It was pointed at the wrong thing.

`FLIP-NUM` is the one I would have sworn was covered. It reverses the finding --
0.885 says the master is *cleaner* than its worst source frame, 1.885 says it is
*worse*, which is the difference between ACQUIT and CONVICT -- and the checker
stayed green because that number lives only in the prose.

## The fix

`bind_report()` in `vr_recheck.py` now parses every verdict row and checks, per
row, the master statistic, the source maximum, the registered source-frame count,
the stated ratio, the verdict against the adjudicated one, and the verdict
against the `1.3x` rule applied to the row's own ratio. It also binds the
headline count to the baseline's verdict counts, and reports adjudicated rows the
report never states. The existing master partition is untouched and still sums;
the binding adds a second partition that also sums.

## Re-commissioned, eleven arms

`vp_flipcommission2.py`: **0 of 11 arms fail to do their job.** NULL green, ten
planted defects all caught.

The arm I added because V-LINEAR's experience predicted it is `RE-LICENSE`: flip
the ratio to `1.500` *and* the verdict to `CONVICT` together, so the report is
INTERNALLY CONSISTENT under the rule. A rule-consistency check alone passes that.
It is caught only because the ratio is bound to the measured baseline. That is
the arm that would have re-licensed a withdrawn conclusion with every number
looking correct.

`DELETE-ROW` is caught by the no-row bucket, so deleting an inconvenient row is
not a way to go green either.

## Scope, stated plainly

This covers `report.md` and `vr_baseline.json`. **My other deliverables --
`ADJ-ndepth.md`, `HALO-coverage.md`, `RECHECK-bands.md`, `AUDIT-envsurface.md`,
`RETRACTION-overshoot.md`, `ROUTE-pyramid.md` -- have no report verifier at all.**
An unverified report is not the same as one that passed, and I am not going to
let those two read alike. `HALO-coverage.md` is the one I would bind next, since
`halo_profile.py` is now scoring another lane's fix.
"""

with io.open(r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\SELFAUDIT-flip.md",
             "w", encoding="utf-8", newline="\n") as f:
    f.write(body)
print("wrote", len(body))
