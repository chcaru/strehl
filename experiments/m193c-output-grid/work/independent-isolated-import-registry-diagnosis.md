# Independent isolated import registry diagnosis

SOURCE/metadata-only. No NumPy import, collector, candidate inspector, control, native call, numerical data, image or model execution. The actual offending alias was not saved. No alias below is identified as the measured failure. An oversized first note draft failed its prewrite size assertion; no file was created by it.

## Retained failure and source evidence

Saved local-image-checker-import-capture-1.json is 58,677 bytes / SHA256 2bfaa94532ea2e90ad3744475c7e9ce0883121e5ac7a83c31f54c453a6081950. Its traceback reaches aliases() after the NumPy import and fails at exact type(module) is ModuleType. Only before-numpy registry progress survives (94 aliases, 94 processed, zero unresolved); that is not the after-import population. No alias/type operand was retained.

Installed NumPy metadata identifies version2.4.4 and permissive BSD-3-Clause/0BSD/MIT/Zlib/CC0 licences. Source below was already in the original plan and was authenticated against its byte/hash bindings. No external repository was opened.

There is a concrete non-module proxy path: numpy/__init__.py:470 imports lib; numpy/lib/__init__.py:18-20 imports _arraypad_impl; _arraypad_impl.py:6 imports typing. Bound Python312 Lib/typing.py:3322-3348 defines io and re as classes with metaclass _DeprecatedType and stores them in sys.modules as typing.io and typing.re. They are not ModuleType subclasses. Replacing exact-type equality with isinstance(value, ModuleType) alone is insufficient. This is a source-supported candidate, not a reconstruction of the missing operand. Primary [typing documentation](https://docs.python.org/3.12/library/typing.html) confirms the deprecated namespaces.

Bound Lib/importlib/util.py:168 defines _LazyModule(ModuleType), whose __getattribute__ triggers exec_module. Normal attribute access, including generic vars()/__dict__ lookup, is therefore not universally observation-only. Python allows customized module lookup; an already obtained globals dictionary has different semantics. [Data model](https://docs.python.org/3.12/reference/datamodel.html#customizing-module-attribute-access), [vars](https://docs.python.org/3.12/library/functions.html#vars). This is an inspector hazard, not evidence the capture encountered _LazyModule. No ModuleType-subclass assignment was found in inspected plan-bound NumPy Python files; compiled extension internals were not examined.

Bound source identities, relative to installed Python312 Lib:

- typing.py: 122,330 bytes / 26506916777c5fb375f98d13824895adb110565a12a9674c03cb596332e13c43.
- importlib/util.py: 11,264 / 5adb3c86ff7b800c60cc78ea5a892ae8fc08f90d97208a7e447e77beb9d50360.
- site-packages/numpy/__init__.py: 27,212 / b16a4f347c6583c878e1973a208564e01686b79cc70911ad0157e05d8eecda37.
- site-packages/numpy/lib/__init__.py: 3,101 / b192ff0453161d346630051695b049fa780c09d93a509f45754de7d12d123048.
- site-packages/numpy/lib/_arraypad_impl.py: 34,445 / ac7fce53a5efa26de5e29d836eb840ad020f8ec8ccf4438dc6d4aa28dcf177a8.

## Bounded representation

Snapshot the entire bounded alias population. Retain one row per alias: None, module/subclass, class proxy or unknown object. Save object/type identity, classification, typed bounded metadata, owner/file authority or unresolved reason. Append a row before validating it; collect discrepancies and refuse after retaining the complete scan. Overflow explicitly means incomplete, with total/visited counts and retained prefix; never silently omit unknown rows.

Use explicit built-in raw dictionary descriptors for genuine modules/classes to bypass custom lookup. Avoid arbitrary getattr, hasattr, vars, repr or str as generic fallbacks. This applies to type/loader labels and ModuleSpec.cached too: cached is an accessor, not a raw field. Retain raw spec dictionary fields or declare a source-bound pure derivation; never force lazy loading to obtain metadata. Unsupported shapes remain unresolved rows. Full alias object identities and primitive metadata before/after inspection must agree, exposing inspection-triggered loading or rebinding.

For the two typing proxies, validate exact alias, class/metaclass and identity with the corresponding class in the raw dictionary of authenticated typing. Bind typing.py as owner; these objects have no separate module file. Do not invent __file__ or accept arbitrary objects because they claim __module__='typing'. Preserve unknown proxies and refuse data admission. Module subclasses likewise need actual type/file provenance, not a blanket exemption.

Proposed cheap controls: a genuine subclass whose ordinary lookup trips a counter while raw inspection does not; an exact source-shaped class proxy; missing/rebound alias or wrong owner/type/file/hash; and an unknown object retained before final refusal. Require original whole metadata hashes/object identities and restoration. None ran here.

## Single audit3 preflight

One isolated audit can perform the revised complete registry/source preflight after imports but before saved numerical payloads, retain it, then perform saved-data checks and recheck registry/files. This avoids a second no-data import without admitting failed capture1 as a baseline. Keep all failures/costs. A new grant must explicitly authorize the changed contract; do not silently replace claimed whole-registry equality with file membership.

Require the original positive/empty file namespace plus named new checker sources, complete aliases/types/proxy-owner associations, same-handle content/identity checks and only source-defined lazy additions at named stages. Unknown preflight rows stop data access. Post-data comparisons detect changes, but do not prove every in-memory callable came from its reported file. Executed cache bytes and dependent native DLL closure remain unverified. Preflight success supplies scoped runtime-source authority, not scientific success, subject completion or geometry admission.
