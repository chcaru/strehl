# Restricted local placement in the native consumer

This is an implementation of the September 14 measured local translation. It
does not estimate a new alignment, replace the global map, or establish a new
image-quality result. Independent controls and the root-owned complete-stack
render decide whether it is usable.

The optional `STREHL_LOCAL_PLACEMENT_FILE` names an absolute JSON file:

```json
{
  "schema_version": 1,
  "source_dir": "D:\\absolute\\source-directory",
  "expected_frame_count": 299,
  "native_geometry": [7032, 4688],
  "support_native": [1332, 1104, 392, 392],
  "taper_native": 32,
  "frames": [
    {
      "file_name": "DSC00150.ARW",
      "transform_bits": [
        "3ff0000000000000", "0000000000000000",
        "0000000000000000", "0000000000000000"
      ],
      "delta_source_native": [0.0, 0.0]
    }
  ]
}
```

The transform bits above are only an identity-schema example. Actual entries
must contain the exact original map's `a.re, a.im, b.re, b.im` binary64 bits.
An absent entry or zero delta leaves the existing gather untouched. The source
directory is canonicalized and all stack paths, frame count, map geometry,
resampler and configured original transforms are checked before the merge.
Unknown JSON fields and unsupported versions, modes, geometry, transform bits,
duplicate files or deltas outside the measured four-native-pixel bound refuse.
The gate-floor `debug` identity-transform diagnostic is incompatible and refuses
explicitly; normal actual/probe operation shares the same correction.

The existing GPU or CPU direct gather remains the base. For each destination
CFA site inside the support rectangle, the source translation is multiplied by
the product of horizontal and vertical cubic smoothsteps. Each smoothstep is
zero on and outside the first/last supported native site, and exactly one at
least 32 native pixels inside both corresponding edges. This uses each site's
native reference coordinate, including its Bayer offset. The weighted delta,
in source-native pixels, is inserted into the original plane-unit translation
as `b += delta * weight / 2`, before the existing optical-profile composition.
Nothing interpolates or blends a corrected and uncorrected image.

Preparation enumerates only affected destination sites and refuses if any
corrected Catmull stencil plus its Malvar radius-two support leaves the active
sensor. The union of the required original CFA samples becomes one unaligned
patch, with an even active-coordinate origin. Black subtraction, WB, Malvar
reconstruction, Catmull sampling and inverse-WB rounded/float conversion use the
existing consumer operations. All replacement values are computed and checked
before assignment. Source CFA is borrowed immutably. No aligned-frame collection
or private noise estimate is introduced.

`warp_frame_fullres_into_planes` invokes this path for the real frame and the
synthetic noise probe; the latter preserves the source path, metadata and
geometry while substituting samples. The same entry point is used by the
confidence reread. There is no observer switch or diagnostic logging here.

Independent verification must choose asymmetric geometry, all Bayer phases,
nonzero decoded active origin, nonidentity original transforms and CA. It must
show that the interior agrees with the existing uniform shifted-map gather,
outside/zero cases remain bit-identical, and malformed or unsupported inputs
refuse. These are implementation claims awaiting that verification, not results
asserted by this author.
