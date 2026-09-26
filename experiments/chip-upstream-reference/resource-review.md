# Independent resource-retry review

VERIFIED by direct inspection of run-2 receipts and the new wrapper: run-2 stopped
at the 24-GiB committed-memory limit after 46.922 seconds. Peak job commitment
was 25,829,523,456 bytes; terminal accounting and clean owned termination are
recorded. Its 299-entry before/after input receipts are byte-identical and no
whole-stack TIFF exists. This establishes resource refusal, not image quality.

No blocker found in the single run-3 wrapper. It checks that actual prior failure,
unchanged prior source bindings and exact prepared identities; compares the entire
new command against the prior command except the fresh output path; and reuses
the fixed runtime, input scans and output decoder. Only job commitment becomes
40 GiB. Wall/CPU limits, 8 threads, batch size 4, all 299 inputs and image settings
remain fixed. The available-memory gate runs after the prehash, immediately before
launch, requires at least 48 GiB and records other named scientific processes
without stopping them. It is a current snapshot, not a reservation or guarantee.
The actual job call passes 40 GiB to the existing bounded helper; finally retains
all 299 posthashes, provenance, runtime and source checks even on failure.

The fresh-directory restriction and decision retain the previous failure and
close this route if the authorized retry fails. Existing whole RGB8/ICC/crop and
native-CFA comparison limitations remain. No quality criterion or renderer
parameter is relaxed. The reviewer performed no vendor or image execution.
This review is frozen; results belong in a separate file.
