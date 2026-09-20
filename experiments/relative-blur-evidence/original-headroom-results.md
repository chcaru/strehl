# Original-code headroom near the annotated highlights

MEASURED by root, independently source/receipt-reviewed without rerun in
original-headroom-review.md. Command actually run:

```
python -I -B -X faulthandler experiments/relative-blur-evidence/original-headroom.py --out experiments/relative-blur-evidence/original-headroom-1
```

The second decoder's copied7032x4688 active-u16 pixels match the complete
retained Rust-source SHA256 for all four inputs. LibRaw's default visible
width is7028, so the check deliberately copies the matched full-buffer extent
inside the live decoder context. No padded zeros or freed views enter counts.

Each fixed broad neighbourhood contains4225 original sites (65x65), mapped
around the held green-reference annotation. Values are original integer codes;
the neighbourhood is not the exact channel-specific consumed stencil.

| Source | Facet-core sites >=15360 | Dark-core sites >=15360 | Nearby-structure maximum |
| --- | ---: | ---: | ---: |
|25|279|224|6431|
|28|272|236|6064|
|33|266|255|5575|
|69|6|877|4797|

Both core neighbourhoods reach16383 in every input. The nearby-structure
neighbourhood has no site at or above15360 in these four inputs. Counts at
exact15360 and at/above16383 are retained separately in result.json.

The stacker's held white level is15360, while LibRaw reports16383. These are
not interchangeable thresholds, and this measurement does not calibrate
physical saturation. It establishes maximum-code samples in the original
highlight neighbourhoods, not exact membership of a future component-tree
branch. It neither proves every frame clipped nor supplies optical focus truth.

This is an eligibility warning for automatic branch selection: blanket
clipped-core refusal may leave the real target unserved. The next generated
screen must preserve explicit clipping refusal and report exact analysis/core
stencil intersections. It must not waive that rule to manufacture coverage.
No image changed and no photographic improvement is claimed.
