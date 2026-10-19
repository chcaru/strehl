# Pinned native rendering research workflow

This workflow uses a separately retained experimental build. It is not the
normal desktop or default CLI quickstart, and a clean checkout does not contain
the bound executable. Use the [main README](../README.md) for the normal build.

Use `scripts/render-native.py` for new Sony ARW stacks. It binds the selected executable by SHA256, records the original file order and hashes, runs the native GPU path, and writes the complete RGB16 TIFF, full-resolution JPEG, overview, command logs and receipts into a fresh output directory.

```
python scripts/render-native.py --input "path/to/capture-folder" --out "outputs/example-current"
```

The default build binding is `scripts/native-build.json`, published after the selected build passes its relevant checks. Its schema is `{ "schema": 1, "executable": { "path": "absolute path or path relative to the repository", "sha256": "actual SHA256" } }`. Missing manifests or mismatched hashes stop the render. The manifest currently selects the locally retained September25 build; executables and large image artifacts are not committed to Git. See `experiments/garnet-spatial-trace/results.md` for its build command, validation and remaining CLI test-configuration failures.

To select a retained build explicitly, supply both `--exe <path>` and `--sha256 <hash>`. To reuse an existing alignment, add `--warp-map <alignment.txt>`; otherwise the runner creates an alignment first. An optional `--exposure=-0.5` applies that explicit viewing adjustment. Without it, the normal automatic tone policy and as-shot white balance apply.

The input must be one directory containing 3–1024 ARW files in lexical capture order. Multi-part stacks must first have one correctly ordered source directory, as in the existing marigold input staging. Subdirectories are not combined implicitly. Originals and retained maps are read-only; the output must be outside the input directory and must not exist yet. Retained maps must use Catmull–Rom sampling; the runner verifies that setting.

Historical `outputs/*/render.py` scripts remain pinned to the old build for provenance. Rebuilding the project does not update those pins. Use a new output directory for corrected rerenders; never replace a historical executable or its receipts. An execution-success receipt is not an image-quality claim: inspect the complete output and independent native-scale regions before declaring an improvement.
