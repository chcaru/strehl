# ROUTE: who holds `pyramid.rs`, and what it breaks

V-REVIEW. Answers ORCH's item 1 and reports a blocking finding for the lane
that holds the file. I did not edit any file outside `experiments/V-REVIEW/`.

## 1. The holder is V-SPEED. MEASURED, not inferred.

`experiments/V-SPEED/hullcommission.ps1:1-2`, verbatim:

```
# Behavioural commission of the STREHL_HULL environment variable added to
# crates/strehl-core/src/pyramid.rs.
```

The lane names the file it added to. Corroborating, not load-bearing:
`experiments/V-SPEED/sweep.ps1:90-91` sets `$env:STREHL_HULL` as a sweep arm,
and `hullcommission.ps1` is dated 20:03 against the file's 19:34 mtime, which
is the right order for add-then-commission.

**V-GATHER is not the author, though its directory contains the same hunk.**
`experiments/V-GATHER/gf-tree-dirt.diff` is a byte-identical capture of the
uncommitted change, same index line `9a789c32..852be93f`. The filename records
what it is: a lane noting that the shared tree it measured against was dirty.
Attributing on file contents alone would have named the wrong lane.

## 2. The change makes a shipping check FAIL. This is the blocking part.

`scripts/check-defaults.py` exits **1**:

```
> --- UNDECLARED (nobody has thought about these) ---
>   STREHL_GATE_FLOOR_SCALE      seen at : gatefloor.rs:120
>   STREHL_HULL                  seen at : pyramid.rs:761
>   STREHL_PYRAMID_WEIGHT_DUMP   seen at : pyramid.rs:703

FAIL: 3 switch(es) are not declared in REGISTRY.
```

**Two of the three are pre-existing and are not V-SPEED's.** `STREHL_HULL` is
an added line in the uncommitted diff, so at HEAD this check reports two. That
attribution is DERIVED from the diff's `+` prefix, not from a second run.

The remedy is the project's own, already written down for the previous instance
of this exact defect (`byte-freezes.tsv:86`): *"it is registered in the same
commit that gives it something to hide."* `STREHL_HULL` needs a `Declared` entry
in `check-defaults.py`'s `REGISTRY` in the commit that lands it.

## 3. What goes wrong if it lands undeclared

`scripts/finalpass.ps1:645` prints the provenance header from the registry:

```
RESOLVED SWITCH STATE (39 registry switches; 0 set)
  Unset switches are listed too:
  an omitted line is indistinguishable from a switch nobody considered.
```

That is a completeness claim, and an unregistered switch falsifies it silently.
The claim would still read "0 set" on a render whose merge clamp was selected by
the environment. This is the shape ORCH propagated today: a check satisfied by an
incomplete enumeration. It has a measured prior cost here. `merge_cmd.rs:2521`
records a registry-versus-code disagreement that "hid a measured +1415 DN of
recoverable background artifact."

## 4. A guard I was about to recommend already exists, and works

I expected to find no test binding the registry to the code. **That is refuted.**
`check-defaults.py:1478` computes `set(found) - set(REGISTRY)` and fails on the
difference. It caught `STREHL_HULL` without my help. The gap is not a missing
instrument, it is three undeclared entries and a red check nobody has cleared.

Cross-validation worth recording: my own scan, written before I found that code
and sharing none of it, counted **48** `STREHL_*` literals in `crates/`. The
tool independently prints `switches found in crates/ 48`.

## 5. Two errors of mine, disclosed

**I asked the provenance question against the wrong artifact.** I first tested
the TIFF `ImageDescription` (619 chars, colorimetry only), concluded provenance
recorded no environment state, and was wrong. Each master carries a ~14.8 KB
`.provenance.txt` sidecar that does. The correct instrument changed the answer.

**My integrity scan reported 52 unreadable files in `acceptance/SHIP-V3`.** That
was a glob defect: `*.tif*` matches `.tiff.ok` and `.tiff.provenance.txt`
sidecars. **26 of 26 real masters are readable in both corpora.** No corruption.
Retracted before it reached a report.

I also nearly filed section 3 as a new finding. It is largely a re-confirmation
of my own `AUDIT-envsurface.md`, which already ranked `STREHL_GATE_FLOOR*` as
unrecorded and HIGH. The genuinely new element is `STREHL_HULL` and the red exit
code. My earlier audit also established that the four `STREHL_DEFECT*` switches
cannot fire on a `strehl stack` run, which corrects an intermediate count of mine
that had listed them as live runtime reads.
