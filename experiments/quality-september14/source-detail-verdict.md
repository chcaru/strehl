# Bounded original-detail check

**VISUALLY OBSERVED: no missing recoverable mark was established.** The baseline resolves the winding fibre and junction marks more clearly than the four sampled original frames. Every sampled original is defocused at the relevant fine features. This sparse sample therefore cannot demonstrate that the stack has retained all available detail, or serve as an in-focus target for algorithm acceptance.

Exactly three additional original files were read: `DSC00027.ARW`, `DSC00079.ARW`, and `DSC00105.ARW` from `D:/personal/macro/requests/misc-diagnostic/3d-printer-piece-cpl`. The previously retained middle-frame displays from `DSC00053.ARW` were reused. There was no additional decode of the middle frame.

Command run:

```text
python -X faulthandler experiments/quality-september14/source-detail-check.py
```

**VERIFIED:** The existing rawler helper and rawpy/LibRaw produced identical raw values over each retained union. The owned process tree consumed 9.28125 CPU seconds, below its 30-second bound, and retained 7,943,390 bytes when checked. Source sizes and modification times were unchanged. Receipts and process accounting are in `source-review-2`.

Two 300×300 output-coordinate regions were chosen before these decodes: fibre at `(3084,3100)` and junction at `(3434,2534)`. The existing baseline map carried each region centre from reference frame 52 into its source frame. Native output origin `(96,64)` and the documented plane centre were included. Origins were rounded to even sensor coordinates to preserve CFA phase; the source images themselves were neither warped nor resampled. The retained source scales relative to reference 52 are 1.0106094 for frame 26, 0.9897996 for frame 78, and 0.9789594 for frame 104. These are mapping parameters, not accuracy or resolution measurements.

I inspected the baseline and all four source RGB crop pairs at native 1:1 display, and checked representative undecoded-to-RGB green planes separately: both green phases for frame 26's fibre and junction, plus frame 78's fibre and frame 104's junction. Raw green displays show one pixel per original same-colour sample, at two native pixels per sample. The source display uses fixed gain and gamma; source LibRaw development differs from the product tone, so brightness and colour are not matched quality evidence.

At the fibre, frame 26 and the existing frame 52 retain the broad winding shape while the thin contour is diffuse; frames 78 and 104 are more strongly defocused. At the junction, the bright lower-edge landmarks remain recognisable but diffuse in frames 26 and 52, and substantially blurred later. No sampled source shows a clearly separate or continuous fine mark that the baseline deletes or doubles.

No sharpness metric, best-frame argmax, noise estimate, or new causal diagnosis was introduced. The desired falsifier—a clearly resolved original mark missing from the baseline—was not found in this allocated sample. Additional source reads stop here.
