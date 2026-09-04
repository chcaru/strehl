# M138 adapter amendment 1 — isolated import repair

**Frozen before rerun:** yes  
**Affected file:** `m138_adapter.py`

The first post-freeze invocation exited before argument parsing:

```text
ModuleNotFoundError: No module named 'comparison_checker'
```

Under this host's Python 3.12 isolated mode, the entrypoint directory is not
placed on `sys.path`. The original source used a normal local import, so no
request, core decision, commissioning control, or output statistic executed.

This amendment replaces that import with an explicit
`importlib.util.spec_from_file_location` load of the sibling frozen
`comparison_checker.py`. The path remains inside the hash-verified checker
bundle. No request schema, output mapping, commissioning bar, core checker, or
valid-input arithmetic changes.

The amendment itself is added to the checker bundle. The complete preregistered
self-test must be rerun from the beginning; the failed startup attempt is not a
commissioning result.
