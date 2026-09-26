# Independent ore102 and rutile105 numerical-repair delivery review

VERDICT: the corrected complete renders remove small artificial block/rectangle
patterns at the inspected glints. This is a bounded repair, not broad glare
recovery or SOTA qualification. The independently frozen ore white-patch target
also improves locally, so the finding is not confined to the author's largest-
change location. Bright washed-out regions, softened texture and colored
microglints remain.

The reviewer did not author the production numerator change or these full
renders. No RAW file, build or merge job was run here. The command below reads
existing TIFFs and receipts, checks bindings, and creates exact native views:

```text
C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -B -X faulthandler experiments/quality-september25/mineral-repair-review/review-deliveries.py
```

`evidence.json` binds that script and inputs. All four complete before/corrected
overviews were viewed for orientation; all twelve unresampled384px native views
were inspected. Old fixed targets come from the earlier mineral native-tiles
receipt. The newly extracted before-target pixels exactly reproduce those old
witnesses. The four largest-change views also exactly reproduce root's helper
outputs; their locations remain selected by change and are not an unbiased
sample of image quality.

## Binding and settings checks

For both deliveries, old and new ordered manifests have identical index,
filename, byte length and original SHA256 for every source:216 in ore102 and228
in rutile105. Rutile's directory was relabeled between runs; source identities
match despite that path change. This audit compares producer manifests and
their unchanged-source receipts, rather than independently reopening RAW files.

The actual retained map, reference, complete placement rows, crop, dimensions,
RGB16 storage and ICC all agree. Ore: reference108, crop[85,57,3347,2231],
6694x4462. Rutile: reference114, crop[68,45,3380,2254],6760x4508. The new
executables match the checked repaired SHA256 beginning `bec4c357`.

Effective merge/render flags agree: seven bands, gate2, exponent2, ramp1.4,
soft selection, mean base, sRGB, MHC, Catmull-Rom and common coverage crop.
Exposure is the same−.3EV for ore102 and0EV for rutile105. The latter's new
explicit0.0 resolves to the same no-exposure mode. Held native GPU/green-probe,
thread and alignment environment settings match. GPU logging changed off→on;
new invocation explicitly disables fine support and CA-before-MHC experiments.
No competing treatment is activated.

Current TIFF files reproduce the hashes in their complete delivery receipts.
Old final-master hashes match both the independent inventory and historical
selected-variant completions. This matters for ore102: the correct old final
is `exposure-minus-03`, not its brighter initial render.

## Photographic observations

**Ore102:** root's change-selected native rectangle[2517,0,384,384] contains a
bright glint near its upper middle. The old version has a conspicuous stepped,
axis-aligned dark/magenta/cyan intrusion through the glint. The corrected
version has a continuous white core with green/cyan surrounding light; the
rectangular intrusion is gone. The broad luminous spread and locally soft
surface detail remain. No claim is made that the brighter continuous glint is
itself more accurate than the physical source.

The independently frozen white-patch target[1398,2748,384,384] gives separate
support: small magenta rectangular ticks along the left dark/white boundary
are removed. The large white patch remains bright and washed out, with the
same broadly visible internal grains. Small blue/cyan specks near the opposite
edge and general color spill remain. This is not recovery of the entire bright
patch. The independent blue-control[3328,1628,384,384] retains its granular
blue/cyan surface structure; no new detail improvement was identified there.

Ore102's whole-image RGB changes must NOT be called widespread repair. Its
automatic-tone log changes from black−.00104/white.52324 to
black−.00099/white.53070, while exposure stays−.3EV and contrast stays.55.
These are rounded log values, not exact captured tone bits. The resulting
global brightness shift confounds raw RGB difference counts. This review
credits the disappearing rectangle shapes only, not global dimming, changed
pixel totals or lower apparent glare.

**Rutile105:** in root's change-selected rectangle[1013,692,384,384], the small
glint near the middle loses its old blocky magenta/cyan cap and becomes a more
continuous white/cyan glint. The effect is small. Soft granular reflections,
colored points and indistinct background texture remain, including the bright
mark near the lower right. The complete image reads essentially the same at
overview size; that view cannot substantiate fine detail.

The independently frozen gold-blades target[4708,2378,384,384] preserves the
long grooves, parallel bright lines and reddish marks. The dark-control
[2428,2428,384,384] retains its scattered blurred glints. No visible broad gain
or loss was identified in either protection target. Their files are not
byte-identical, so this is a bounded visual observation, not an identity claim.
Rutile's rounded tone report is unchanged at black−.00021/white1.16450 and
contrast.55; exact-tone bit identity was not measured by this delivery audit.

## Scope of acceptance

The additional deliveries support transfer of the localized rectangular-
artifact repair to more mineral captures. They do not establish that all
remaining glints are artifacts, that captured glare was removed, that all
sources are unclipped, or that ghosting and occlusion halos are solved. No
sharpness/noise metric is used. Show the user the COMPLETE corrected outputs
when presenting this repair, with the native inspections only as supporting
evidence.
