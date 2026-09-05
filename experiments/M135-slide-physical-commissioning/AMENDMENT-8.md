# M135 slide commissioning amendment 8

Status: **FIXTURE-ONLY REPAIR AFTER THE SEMANTIC GUARD WENT RED**

The first run of amendment 7 is preserved as
`commission-run3-failed.json`, SHA-256
`ab78eaa81b803543486571337914cfd7edd991163f7c5401d66fe08e720b6086`.

Both red controls stopped before the selector they were meant to challenge:
their synthetic `REFERENCE_ROLE_ABSENT` artifact omitted the newly required
`all_required_roles_present=false` evidence.  Add that one fixture field and
rerun.  No production predicate, status, threshold, or source-data path
changes.
