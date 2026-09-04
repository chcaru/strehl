# M164 real-pair audit — amendment 3

Status: **FROZEN AFTER RUN 3 FAILED, BEFORE RUN 4**

Run 3 completed `run_real` and atomically wrote its complete result, but the
console-reporting loop then indexed `verdict` on an exception record that did
not contain that key. The outer failure handler consequently replaced the
complete artifact with the printer traceback. The retained failure artifact
is `out/realpair-run3-print-failed.json`, SHA-256
`AE67C1098B8DC91B784B12E5C5B2D401D5561B6512B2B4807CBAC341E29742D8`.

This amendment changes result serialization only:

1. exception records receive the explicit verdict
   `UNADJUDICABLE_EXCEPTION`, fixed-site count, and zero eligible sites;
2. console output uses fail-safe dictionary access for invalid records; and
3. no site, eligibility rule, scientific threshold, adapter, pair, or
   transfer family changes.

