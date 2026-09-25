# Native-tile correction to mineral diagnosis

The initial640px output views exceed the project's commissioned viewer limit (AGENTS48). They are not evidence for fine detail, defect width or absence of defects. All whole-image1617px views remain orientation/delivery images only. The numerical RAW census is unchanged.

Ran:

```text
python -I -B experiments/quality-september25/minerals/native-tiles.py
```

This makes exact384px integer crops from the previously converted native output640px regions, with no resize, color transform or additional rounding. `native-tiles.json` records each absolute output origin, source and file hash. Ten files were generated. Four were inspected at384px: ore100 white patch and blue control; garnet104 white facet and red control.

The garnet fine-color anomaly is **confirmed in a384px native tile**, `104-white-facet-native384.png`, output origin(4668,1858). Squared magenta/cyan patterned patches are visible around output(4782..4823,1996..2036) and(4881..4909,2067..2109), within/along the bright facet. Bounds are approximate visual localization, not a measured width statistic. Their cause remains unverified; they are not diagnosed merely as sensor clipping, merge error or display tone. Preserve this tile as an independent adverse target for the rendering experiment.

The ore384px bright tile, origin(1208,748), contains distinct dark grains within the real bright patch, with colored grains around its edge. A candidate that simply makes the entire patch grey/flat or deletes it cannot claim glare repair. Blue protection tile origin(2908,2768) contains a strong blue diagonal facet and fine markings; garnet red protection tile origin(3068,1908) contains genuine red transmission and bright microfeatures. These are textured protection targets, not flat-noise controls.

The source green witnesses were320px CFA-quad views and thus within the viewer limit, but they have half the native spatial grid, nearest-quad gathering and a different grayscale display transform. Their role is confirming source presence of broad reflection/texture and source clipping counts. They do not establish precise source/output blur ratios or chromatic detail retention.
