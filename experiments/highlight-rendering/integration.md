# Root-owned integration and commands

No production crate files were edited by this experiment's author. Apply only
after other active source-bound runs finish and all new authors freeze.

Use this guard for all four additions:

```rust
#[cfg(all(test, feature = "native-direct-planes", feature = "native-correction-variance", feature = "native-gpu-gather"))]
```

In image_out.rs add the guarded module:

```rust
pub(crate) mod highlight_rendering {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/highlight-rendering/image-out-bridge.rs"));
}
```

At the start of actual `develop_pixel`, before its existing matrix expression,
insert the guarded optional branch:

```rust
if let Some(value) = highlight_rendering::override_pixel(lin, dev) {
    return value;
}
```

In actual `write_demosaiced`, immediately after
`let dev = &resolve_tone(dev, || tone_from_mosaic(&m, dev));`, insert guarded:

```rust
highlight_rendering::record_resolved(dev);
```

In merge_cmd.rs add the guarded module:

```rust
pub(crate) mod highlight_rendering_replay {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/highlight-rendering/merge-replay.rs"));
}
```

The sibling `merge_cmd::full_stack_source_prior` module must be present from
that experiment's independent integration. Its `read_cache` and metadata
getters are the agreed API. Fresh CLI compilation is mandatory. Shared build
`sources.json` must include both adapters, controls and actual crate hook files.
Do not change authored sources after the shared build without rebuilding.

```text
python experiments/highlight-rendering/run.py controls --build SHARED_BUILD --out experiments/highlight-rendering/controls-1
python experiments/highlight-rendering/run.py replay --build SHARED_BUILD --controls experiments/highlight-rendering/controls-1 --cache FULL_CURRENT_CACHE_JSON --current RETAINED_USER_FINAL_TIFF --out experiments/highlight-rendering/replay-marigold-1
python experiments/highlight-rendering/run.py views --run experiments/highlight-rendering/replay-marigold-1 --out experiments/highlight-rendering/views-marigold-1
```

Root substitutes existing absolute paths. Exactly four independent tests run
with one test thread; the full factorial is one ignored exact test, also with
one test thread. Test execution is not photographic admission. All four whole
outputs are retained; the current arm is shown before candidates. The driver
does not create an experimental production preset or apply a preferred arm.
