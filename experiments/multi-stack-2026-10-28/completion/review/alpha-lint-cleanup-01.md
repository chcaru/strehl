# Shared alpha/export lint cleanup01

AUTHOR FIX, root-assigned: only four exact textual replacements in two files. `as_chunks::<3/4>().0.iter()` retains the same complete RGB/RGBA chunk order and drops the same nonexistent remainder. `is_multiple_of(2)` preserves the even-dimension guard. Test range membership is the same half-open2..10 and2..9 predicate. No numerical expressions, color arithmetic, alpha semantics, TIFF tags or publication operations changed. Inherited image_out.rs chunks_exact diagnostics were deliberately left unchanged.

VERIFIED command actually run outside the sandbox for the atomic filesystem checks:

```powershell
python -X utf8 experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/alpha-lint-controls-01 --cwd . -- cargo test --locked -p strehl-cli --lib session_alpha_output::tests -- --nocapture
```

Fresh Compiling strehl-cli;2passed,0failed, exit0. Controls verify full-support tone equals ordinary, missing storage cannot influence tone, all RGB values/ICC/description/resolution survive alpha publication, and the actual demosaic-support mask has the required transparent boundary/hole. Complete logs/resource receipt retained. This narrow pass does not make the previous strict CLI clippy command pass; root schedules the final lint rerun after all owners finish.

Exact before/after bytes and replacements are recorded in [alpha-lint-cleanup-01.json](alpha-lint-cleanup-01.json). Final SHA256:

- `crates/strehl-cli/src/session-alpha-output.rs`: `1094155e9119706ee8fefb57017efe59e53c54f3fbb01828cd7aec2b38a5e343`
- `crates/strehl-cli/src/image_out.rs`: `9ee181b62e594a0b5911def456b032fa1aa947d8f1e07344ab8ae638f95874c8`
