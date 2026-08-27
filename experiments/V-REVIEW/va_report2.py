import io
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-aura-ship.md"
T = io.open(P, encoding="utf-8").read()
ADD = """
## Addendum: the three binary claims, audited

Raised as an urgent addendum to this task. Adjudicated rather than accepted.

### The missing build is not missing

**REFUTED.** `066A87ABF8C4D337539ADBA17A9453ABE93728360816700C43E6852099F0437B`
is present at `C:\\dev\\strehl-out\\V-REVIEW\\bin\\strehl-pinned.exe`, 9,716,736
bytes. The original aura renders **are** reproducible, and the README caveat
should not be strengthened to say otherwise.

The absence report is an artifact of the search, not of the filesystem, and the
mechanism is measured rather than supposed:

| search pattern | paths | distinct builds |
|---|---|---|
| exact name `strehl.exe` | 159 | 63 |
| any `strehl*.exe` | 301 | 165 |

An exact-name search cannot reach 102 of the builds on this machine, including
this one, because the file is named `strehl-pinned.exe`. Twenty-six distinct
filenames carry builds it cannot see, among them `strehl-base.exe`,
`strehl-pre.exe`, `strehl-post.exe` and every Cargo hash-suffixed artifact.

> **A search narrower than the thing it is looking for returns the same empty
> result as a search that looked everywhere.** "Not found" is a statement about
> the query until the query's reach has been measured.

Nothing in the aura verdict depends on this. The re-measurement was made on the
shipping pin, which is a stronger footing than the build it replaces.

### The mislabelled pin is real

**CONFIRMED.** `C:\\dev\\strehl-out\\PIN-V3\\strehl.exe` hashes
`B50EABC12D16B29095AAE82240698F3D51BFB64482D4993725437B4CE11A7C99` and appears
in no seal of any corpus, at exactly 9,568,768 bytes.

### The pin directory is mostly not pins, and the size collision is worse

**CONFIRMED, with the count corrected upward.** Sealed corpora and their seals:
`PINTEST` and `SHIP-V3` both name `15EA7346`, `SHIP-V4` names `44C2F2CD`.
Against those, `acceptance-pins` partitions as 2 sealed and 3 unsealed, summing
to the 5 pins present.

| build | size | standing |
|---|---|---|
| `15EA7346` | 9,568,768 | seals PINTEST and SHIP-V3 |
| `44C2F2CD` | 9,568,768 | seals SHIP-V4 |
| `B50EABC1` | 9,568,768 | unsealed, sitting under a directory named for a pin |
| `F663B703` | 9,568,768 | unsealed |

**Four distinct builds share that byte count, not three.** The fourth,
`F663B703AA685129`, was not in the addendum.

### My own renders

Every artifact produced for this task carries a seal and a provenance file
written at render time, and every seal matches the pin the corpus names:
12 sealed and correct, 0 otherwise, summing to the 12 artifacts rendered.

The earlier `geom` and `halo2` renders still carry no seal, deliberately. That
refusal is now doubly vindicated: a guessed hash would have been a certificate
for a build I could not identify. Since that build turns out to still exist,
those renders can be re-made and sealed honestly rather than stamped.
"""
io.open(P, "w", newline="\n", encoding="utf-8").write(T.rstrip("\n") + "\n" + ADD)
print("appended;", len(T.rstrip() + ADD), "chars")
