import io, os
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-aura.md"
t = io.open(P, encoding="utf-8").read()

old_sent = """> On `flower-bud-alone-cpl` the estimator does put a markedly stronger dark aura
> around the subject than the pyramid does, and the pyramid is the current
> default, so that specific complaint is addressed. The 28.5x multiplier is not
> a number to quote: it is specific to that subject and to one choice of mask
> and zone. On a second subject the two merges differ by **1.02x**, and on the
> original subject the ratio moves between **1.24x and 17.70x** as the mask and
> zone are varied, because the quantity it divides by passes through zero."""
new_sent = """> On `flower-bud-alone-cpl` the estimator does put a markedly stronger dark aura
> around the subject than the pyramid does, and the pyramid is the current
> default, so that specific complaint is addressed. The 28.5x multiplier is not
> a number to quote: it is specific to that subject and to one choice of mask
> and zone; on that subject the ratio moves between **1.24x and 17.70x** as the
> mask and zone are varied, because the quantity it divides by passes through
> zero.

**The clause about a second subject that stood here has been withdrawn.** It
read that the two merges differ by 1.02x on `lead-1-cpl`. That measurement is
sound but `lead-1-cpl` does not present the dark-subject-on-bright-ground
geometry the claim names -- its `dark_ratio` is 1.57 against this subject's
4.52 -- so it bounded the claim's generality rather than refuting its mechanism.
The generality question is settled on subjects that do present the geometry in
`docs/research/V-REVIEW-geometry.md`, which supersedes section 3 and the first
paragraph of section 4 below."""
assert old_sent in t, "sanctioned sentence not found"
t = t.replace(old_sent, new_sent)

old_h3 = "## 3. What kills the general form: a second subject\n\n`lead-1-cpl`, identical treatment:"
new_h3 = """## 3. A second subject -- SUPERSEDED

**This section's conclusion does not hold.** `lead-1-cpl` was later measured to
be off-geometry for this claim, and a mask defect affects the numbers below: the
fixed percentile sweep was built for a subject occupying a fifth of the frame and
under-covers one occupying two fifths. The readings are retained for the record.
See `docs/research/V-REVIEW-geometry.md`.

`lead-1-cpl`, identical treatment:"""
assert old_h3 in t, "section 3 header not found"
t = t.replace(old_h3, new_h3)

old_lim = """Two subjects is not a corpus. `lead-1-cpl` may not present the dark-subject-on-
bright-ground geometry the claim names, and I did not verify that it does; if it
does not, it bounds the claim's generality rather than refuting its mechanism.
Either way the multiplier remains a one-subject number."""
new_lim = """**Resolved, against this section.** `lead-1-cpl` was measured and does *not*
present the geometry the claim names, so it bounds the claim's generality rather
than refuting its mechanism. Two on-geometry subjects were then rendered and
measured; the direction holds on both, the magnitude does not. See
`docs/research/V-REVIEW-geometry.md`. The multiplier remains unquotable, for a
second reason established there: a common-mode level shift moves the ratio while
leaving the physical difference bit-identical."""
assert old_lim in t, "limits paragraph not found"
t = t.replace(old_lim, new_lim)

with io.open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(t)
print("patched", P)
