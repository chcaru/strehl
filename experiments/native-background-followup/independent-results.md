# Independent result: upper-right RAW inspection
VERIFIED from saved receipts: this fixed diagnostic stopped before any views.
Four decode children exited0; analysis exited1 at the whole-patch white gate.
It was an assertion, not a decoder crash or resource-limit intervention.

Both512x704 ROIs match:720896 sensels total, with all eight phase-pair hashes
equal and zero different codes. This is1,441,792 payload bytes plus headers.
Frame0 has22437 codes >=15360; frame104 has zero. No streak location, persistence,
shape or physical cause follows from these counts or from decoder agreement.
The source order confirms both comparisons completed before the first view.

Important qualifier:15360 is strehl/M61's white level; LibRaw records16383.
Thus the count is above the product threshold, not a demonstrated count of
physically saturated sensor sites. LibRaw visible width7028 also differs from
M61 active width7032; the compared ROI is safely inside both and exactly agrees.
No claim about unexamined borders or complete decoder equivalence is warranted.

The broad gate was obeyed and its failure must stay recorded. I accepted it in
source review, but zero high codes anywhere in the large transport-support ROI
is unnecessarily strict for a descriptive mark-localization question. It is
relevant to radiometric fitting/correction and can obscure a mark locally;
the receipt does not say whether either fixed or mapped target is affected.
This is a scope-design miss, not evidence that the target is unusable.

Most efficient next decision: close this allocation as decoder-agreement-only.
If continuing, explicitly commission inspection of the already-saved full ROIs,
with both15360/16383 masks visibly marked and counts in the unchanged fixed and
mapped target extents. Retain all pixels and the original failure; do not change
the old gate/crop and rerun it. No additional RAW decode is needed. Physical
dust, correction fidelity and radiometric estimates remain outside that step.
All seven plan source bindings match disk. Decode-comparison SHA256:
44d187f25f0bc84c272b776981e1a662720bbf6f82ce17ce1feca39122a1a602.
Five receipts sum to1.953125 owned CPU seconds and2.015wall seconds;
peak job commit125128704bytes. All have terminal accounting, no cleanup errors,
and no termination attempt. No reviewer pixel readout, output generation or rerun.
