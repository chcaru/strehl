# V-ENVSURF regeneration recipe

All scratch for this lane is DELETED and is fully regenerable from the
read-only originals plus this file. Nothing was kept: no TIFF, no warp cache,
no pinned binary copy. Every number published in docs/research/V-ENVSURF.md was
produced by the harness below.

## Inputs (read-only, not owned by this lane)

    subject   D:\personal\macro\coffee-bubbles      19 ARW frames
    subject   D:\personal\macro\109MSDCF            used only for the DEFECT arms
    binary    <scratch>\strehl-pinned.exe           copy of target\release\strehl.exe

## Binary identities (the shared binary moved three times during the audit)

    EE7A302963B7657CEBAE5BAFB5D8E5628E41EBF92213EB935401CEDDF37C4C5C  00:01:35  9858048  ba34142806cf
    55E0C07E8BC74DAB7BEAAE3890458F5637C9C813EBEB2A69B9D34B9D9B6F62A7  01:01:49  9861632  165074a1606a-dirty
    B2EC82935182E754B57223FCAFC0250FCF8BEB9B4A2960D1B60ACCD2749DF41F  01:43:25  9861632  c9f557f61e6f-dirty

Sections 1-10 of the report describe the FIRST. Section 11 re-verifies on the THIRD.

## Command lines

Pyramid, the shipping default path (no --merge flag):

    & <pin> stack <subject> --out <scratch>\run.tif -l 3 --srgb

Estimator control arm:

    & <pin> stack <subject> --out <scratch>\run.tif -l 3 --srgb --merge estimator --photometric off

Deeper bracket, used for STREHL_SMOOTH_HUBER and the robust-election N check:

    & <pin> stack <subject> --out <scratch>\run.tif -l 19 --srgb

## Harness (PowerShell), one arm

The clear-all step is mandatory. Without it an arm inherits a previous arm's
variable and you measure the wrong knob.

    Get-ChildItem env: | Where-Object {$_.Name -like 'STREHL_*'} |
        ForEach-Object { Remove-Item "env:$($_.Name)" }
    Set-Item -Path "env:<VAR>" -Value "<VALUE>"
    if (Test-Path $out) { Remove-Item $out -Force }
    & $exe stack $subj --out $out -l 3 --srgb 2>&1
    $rc = $LASTEXITCODE
    $h  = (Get-FileHash $out -Algorithm SHA256).Hash
    Remove-Item $out -Force          # hash immediately, then delete

## Method rules that the numbers depend on

1. Every arm has a matched unset control on the identical command line. An exit
   code is not a measurement of the knob you set unless the unset control on the
   same command line returns something else.
2. The comparator was commissioned before any null was trusted. See
   commissioning.tsv: the baseline is deterministic across two runs and -l 4
   reads DIFFERENT.
3. The pin was commissioned, not assumed: one arm run from the shared binary and
   from the pinned copy produced the same output hash and byte count.
4. Bucket is assigned from the variable set ALONE on the shipping default
   command line. A variable needing a companion is bucketed on its
   alone-behaviour and annotated cond: in the report.
5. Path-valued variables are scored on whether the artifact appears, not on
   whether the image changes.
6. Garbage is the literal string zzznope, which names nothing in the tree.

## Known trap

--merge estimator WITHOUT --photometric off exits 1 on coffee-bubbles with
"U3 the eroded low-detail region keeps only 0 px (minimum 1024)". That exit code
belongs to the subject, not to any variable under test.
