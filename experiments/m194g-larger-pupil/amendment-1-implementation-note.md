# Amendment1 implementation handoff

2026-09-07. Implemented only after prospective amendment/review commit
`01d4e52b`. No counter, private control or profile was executed during this
implementation. Root retains source/command commit and execution ownership.

The fixture changes exactly two elapsed values,60/120 to180/240. In
`preflight.py`, only the matching default constants, fixture hash, exact
`AMENDMENT_HASH`, run-entry amendment check and source-list amendment entry
changed. The original preregistration remains required. The amendment is
therefore copied by the existing snapshot loop and checked again through
unchanged before/after source comparison.

Final source pins:

- preflight.py: `c162c2651b1fd3e8345f08c0c9cd5edf5e100d94d7958c5dedde1d791a18763c`
- fixture.json: `e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb`
- amendment-1-counter-budget.md: `205ba1ac42e8325eb7d1ede41e05399776eddf7d80a99ecb3ba12b1931f73a99`

Read-only `git diff` shows no changes to any selector, stream, cut, coverage,
mass, clock-check, work/storage or completion-validation body. The fixture's
future numerical-render and accuracy records remain unchanged. No source
restoration, Git mutation or broad formatting was performed.

The original preregistration still hashes
`d0c570ec892a2c3e40b90c0f7eef2a9ff0649dd53bc34adee6b6bc65280f14c8`;
geometry remains `24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3`;
loader remains `222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76`;
the failed historical profile harness remains
`fc1dd81cf3c6dbccdb46830dcffb98a91b21f05f2a89089d9f40c85f253d0020`.
Historical control passes are not relabelled as tests of this revision. The
independent affected-policy controls must pass before a fresh intended release.
