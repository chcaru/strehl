# M135 slide commissioning amendment 5

Status: **INDEPENDENT ADVERSARIAL REVIEW FINDINGS FIXED BEFORE COMMIT**

A read-only `gpt-5.6-sol` code-review pass found four fail-closed defects after
the first source freeze:

1. artifact config/source hashes used working-tree bytes while the lane forces
   LF in Git;
2. `summarize` did not re-check every parent-artifact hash link;
3. role assignments could name invented source-file IDs and a syntactically
   valid but nonexistent matched-flat manifest;
4. the flat stage could authorize the existing M135 core with four modulo
   splits of one ladder and did not bind its ledger to the role-gate artifact.

The repair uses universal-newline-normalized hashes for source/config text,
checks the complete artifact chain, resolves every role source hash inside its
declared inventory group, reads and hashes the matched-flat manifest, binds the
flat ledger to Stage D, and makes the one-ladder flat stage categorically
insufficient for physical binding.  The existing core remains commissioned on
an independent synthetic four-stream `NO_DETAIL` plant, but the burned slide's
modulo splits can never invoke it.

No physical bar or preregistered selector is relaxed.  No authorized capture
was opened during the review or repair.
