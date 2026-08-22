# Workstream E — Plugin Architecture for a Rust Focus-Stacking Application

**Status:** research complete. Every factual claim below is labelled **VERIFIED** (I fetched and read the primary source, and the URL/file is cited) or **UNVERIFIED** (could not confirm — with the exact URL or query that failed).

**Date of crate/version facts:** 2026-08-22, from the crates.io API (`https://crates.io/api/v1/crates/<name>`).

---

## 0. Scope and method

Four parts, as briefed:

1. A rigorous reading of the Cordis paper (`github.com/cordiverse/paper`), correcting the owner's summary where it is wrong.
2. The Rust plugin design space, with production examples and honest numbers.
3. Prior art in pluggable image-processing pipelines.
4. A dense, opinionated recommendation, staged into v1-minimum and don't-foreclose.

**Method / discipline.** I fetched the Cordis PDF (`https://raw.githubusercontent.com/cordiverse/paper/main/paper.pdf`, 2,140,840 bytes), extracted all 88 pages / 280,285 characters with `pypdf`, and read §1–§6 directly. For crates I used the crates.io JSON API rather than memory. For darktable I read the C headers rather than the (404ing) docs. For wasmtime I fetched the **raw markdown** of the proposal-support table because the rendered mdBook page strips tables.

**Fetches that failed (recorded so absence is not mistaken for evidence):**

| URL | Result |
| --- | --- |
| `https://darktable-org.github.io/dtdocs/en/development/pixelpipe/` | 404 |
| `https://docs.blender.org/...` (Blender OSL / GPU shading) | 403 — **Blender's node/OSL GPU story is NOT verified** |
| `https://docs.rs/bevy_render/latest/bevy_render/render_graph/index.html` | 404 |
| `https://docs.rs/bevy/latest/bevy/render/render_graph/index.html` | 404 |
| `https://raw.githubusercontent.com/bevyengine/naga_oil/main/README.md` | 404 (used the GitHub HTML page instead) |
| `https://docs.rs/naga_oil/latest/naga_oil/compose/index.html` | returned an essentially empty page |
| `https://nix.dev/manual/nix/2.24/store/derivation/` | 404 (used raw markdown from the NixOS/nix repo) |
| `https://gstreamer.freedesktop.org/...` | 503 twice (used GitLab raw markdown) |
| `https://docs.rs/wgpu/latest/wgpu/struct.Device.html` (`as_hal`) | fetch returned only the error-scope section; **raw-Vulkan-handle export from wgpu 30 is UNVERIFIED** |

**Not investigated at all** (flagged honestly, not padded): OBS shader plugins; `rerun`'s extension model; published wasm-vs-native benchmarks for image workloads (I found none and have **not** invented numbers — the wasm argument below is structural plus explicitly-labelled derived arithmetic).

---

# PART 1 — The Cordis paper

## 1.1 Bibliographic (VERIFIED — read from the PDF)

- **Title:** *A Programming Paradigm for Spatiotemporal Composability*
- **Authors:** Yifan Shi (Peking University / DeepSeek-AI), Wei Zhang (PKU), Tianyi Cui (DeepSeek-AI)
- **Draft of:** August 13, 2026. 88 pages. Preprint under active revision (contact `shigma@cordis.io`).
- **Repo:** `https://github.com/cordiverse/paper`; the framework is `https://github.com/cordiverse/cordis`.

Important framing fact: **the paper contains no benchmarks.** §5.3 says so explicitly (see §1.7).

## 1.2 The problem it claims existing plugin systems fail to solve (VERIFIED, §1)

The paper names two *orthogonal* dimensions of **dynamic** composability, each with a well-solved *static* analogue:

- **Temporal composability** — when a component is removed, every modification it made to the shared environment must be completely and safely reversed. Static analogue: lexical scoping, RAII, bracket patterns.
- **Spatial composability** — components must declare, discover and resolve inter-component dependencies in a structured, verifiable way. Static analogue: module import resolution.

**Motivating measurement (§1.2.1, VS Code).** The extension host cannot unload an individual extension's code. Of the top-100 extensions by installs (Marketplace data retrieved June 9, 2026), **87 contain executable code** and therefore require a host restart on removal. `deactivate` is only a graceful-shutdown hook, and it **separates effect disposal from effect creation, violating locality of concern**. Only **7 of the top 100** declare `extensionDependencies` on a non-built-in extension, and `vscode.extensions.getExtension(...).exports` is typed `any` — so there is no checked interface between extensions.

**§1.2.3, the coarse-grained workaround.** Operating systems give temporal composability at *process* granularity; container orchestrators give spatial composability at *service* granularity. The costs: each restart discards process-local state (caches, connections, partial computations) and rebuilding "takes seconds to minutes"; and container-level orchestration cannot express dependencies between components that share an address space, while adding network overhead for what could be local calls.

## 1.3 Contribution 1 — revertible effects (VERIFIED, §3.1)

An effect is modelled as `Γ → Γ × (Γ → Γ)`: applied to a context it yields the modified context **plus an explicit inverse**.

- **Def 1, twisted composition:** `(f₁,g₁) ∘ (f₂,g₂) := (f₁∘f₂, g₂∘g₁)`. This makes `(Γ→Γ) × (Γ→Γ)` a monoid `𝔗Γ` — note the inverses compose in the *opposite* order, which is where LIFO comes from.
- **Def 2, effect context:** `∂Γ := Γ × (Γ→Γ)`, a pair `(γ, φ)` where `φ` is the **accumulator**, the composite of all inverses so far.
- **Def 3, `track`:** `track(f,g)(γ,φ) = (f(γ), φ∘g)`.
- **Thm 5:** `track` is a **monoid homomorphism** from `𝔗Γ` into `∂Γ → ∂Γ`. (This is the technical heart: sequencing effects and sequencing their disposal are the *same* algebraic operation.)
- **Def 6, `recover`:** `recover(γ,φ) = (φ(γ), id)`.
- **Thm 16:** reverting in **LIFO** order requires no additional hypothesis.

**Independence (§3.1.3) — this is the subtle part.** To revert *out of order* — withdraw one component while a later component's effects stand, or interleave several components' effects — you need **Def 19 independence**: every transformation of one effect must commute with every transformation of the other (both the forward maps *and* the inverses they yield), and neither may disturb the inverse the other yields. **Cor 21:** pairwise-independent effects can be reverted in *any* permutation and still reach `γ₀`.

## 1.4 Contribution 2 — reactive coeffects (VERIFIED, §3.2)

The coeffect context is `Σ := (k : K) ⇀ 𝒱ₖ`, a **dependent partial function** from keys to per-key value types.

- `get(k)` requires `k ∈ dom(σ)`.
- `set(k,v) = σ ↦ (σ[k↦v], λσ'. σ'∖k)` — **`set` has type `𝔈*Σ`, i.e. provision is itself a revertible effect.** Registration and deregistration are therefore one code path, not two.
- A **specification** is `d ⊆ K`; satisfaction `σ ⊧ d := ∀k∈d. k ∈ dom(σ)` — decidable.
- **Def 26, `notify_d(σ,σ')` ∈ {activating, deactivating, neutral}.** *Activating* ⇒ run the component's effects **with tracking**. *Deactivating* ⇒ apply the accumulator.

### Isolation and interception (§3.2.3)

**Def 27** distinguishes two ways of realizing an operation:
- **in-place realization** — mutate, and return a nontrivial inverse;
- **derived realization** — leave the input intact, return a fresh *derived* context, inverse is the identity; recovery is simply "discard the derived context".

**Isolation.** `Σiso := (K ⇀ R) × ((r:R) ⇀ 𝒱ᵣ)` with `isolate(k,r)` — a two-layer resolution `k → ρ(k) → σ(ρ(k))`. The paper calls this "a runtime ad-hoc polymorphism system": different regions of the tree can resolve the same key to different *realms*.

**Interception.** `intercept(k,ν)` with a per-key metadata monoid `(ℳₖ, ⊕ₖ, εₖ)`; `get(k,μ) = σ(k)(μ ⊕ₖ ι(k))`, and this is **right-biased so the enclosing context's metadata overrides the component's own declaration**. Because it is consulted at *read time*, interception can be changed at runtime **with no reload**.

## 1.5 Contribution 3 — the context paradigm (VERIFIED, §3.3)

Everything is unified into `Γ∞ := μΓ. Γ × (Γ→Γ) × Σ`. The paper's claim: *"Every interaction between a component and its environment passes through this single entity."* Note that `Σ` here subsumes **all** shared mutable state, not merely dependency wiring.

**Observational equivalence (§3.3.2).** Exact state recovery is an idealization: `free` does not restore the heap layout `malloc` disturbed; a generative name is not restored. So all equalities are read **up to `≃`**, assembled from per-key equivalences `≃ₖ`, and the part of a state that no key binds is simply forgotten. **Lemma 35:** indistinguishability `≈𝒜` is the coarsest relation the operations respect.

**The single most actionable observation in the paper for us (p.25):**

> *"A key whose value is a table of entries added and removed independently is commutative, registration of a route or of an event listener being the representative case… A key whose value is an ordered chain is not, since a middleware inserted before another sees a different request, and neither order can be withdrawn without disturbing the other."*

- **Thm 40:** operations at *distinct keys* are independent outright.
- **Thm 42:** coeffect-mediated effects are independent if every shared key is commutative.
- **Decomposition principle:** the commuting part is carried by **effects**; the order-sensitive part must be carried by **coeffects** — LIFO via the accumulator *within* a component, and by a declared dependency *across* components.

## 1.6 Contribution 4 — the calculus and its metatheory (VERIFIED, §4)

**Component:** `ℭΓ := 𝔇Γ × 𝔓Γ × 𝔈*Γ`, i.e. the triple **(d, p, e)**:
- `d` — coeffect specification (what it requires),
- `p` — provision (the keys it may provide; nothing outside `p` may be written),
- `e` — witnessed effect function (what it installs, together with its inverse).

**Fiber** — an instantiation: `⟨d, p, e, π, σ, τ, θ⟩` with parent `π`, own coeffect table `σ`, retirement flag `τ`, and lifecycle state `θ ∈ {Inactive, Active(g, ω)}` where `g` is the accumulator and **`ω` is the *committed view*: a map from each declared key to the *name of the fiber that provided it* at the moment the transition committed.**

**Registry** `F_γ : 𝔑 ⇀ fibers`, a tree rooted at `root`. `σ_γ = ⋃{σ_m | m ACTIVE}`; provisions of distinct fibers are disjoint, so each key has a unique `provider_k(γ)`.

`target_n(γ) = ⊥` if the fiber is retired or `¬(γ ⊧ d_n)`, else `k ↦ provider_k(γ)`. The system is `quiet(γ)` when every fiber has reached its target. **The lifecycle is driven by comparing the committed view `ω` against the target view** — and the paper is explicit about why identity rather than value: *"recording a provider rather than a value is what makes the comparison usable, since a different fiber providing an equal value would otherwise compare equal."*

**§4.3 relaxes the idealizations** — dropping atomicity, immediacy and infallibility: withdrawal ordering; **iteration** (effect iterators that yield inverses step by step, with a guard checked at step boundaries); **asynchrony** via **inertia** (a transition already in flight runs to completion, then chains into the opposite transition if the target moved meanwhile); and **failure** (`FAILED = Inactive(ξ)`).

**Metatheory (statements verified by extraction from the PDF):**
- **Thm 61 — recovery exactness.**
- **Cor 62 — terminal recovery: a departing fiber leaves nothing behind.**
- **Thm 63 — ordering: a fiber begins a transition only where its dependencies are provided.**
- **Thm 66 — progress (quiescence), given an acyclic `≺`, bounded effect length, finitely many names.**
- **Thm 73 — confluence: the quiescent state is a function of the final configuration alone**, regardless of the order in which the loader performed instantiations and retirements.

## 1.7 Implementation and case study (VERIFIED, §5)

- **`ctx.effect(callback)` is the *sole* primitive through which the context is mutated.** Coeffect provision and component instantiation both reduce to it. Algorithm 1 folds yielded inverses LIFO, uses an `armed` flag for at-most-once disposal, and **prepends `dispose` to the parent's `ctx.dispose`**, so a child's inverse is itself an effect on the parent.
- **The runtime does NOT verify the witness.** The paper: *"that the inverse recovers the effect it accompanies is an obligation on the component author rather than a property the runtime verifies."* This matters enormously for us — see §1.9.
- Slots: `@@store` (σ), `@@isolate` (ρ), `@@intercept` (ι).
- Theory↔implementation map (Table 2, p.55): `fiber.inject` = `d`; component `provide` = `p`; `fiber.apply` = `e`; `fiber.dispose` = the accumulator; `fiber.committed` = `ω`; `fiber.inertia` = the in-flight transition handle; `ctx.use` = instantiation.
- **Algorithm 3 (`notify`) iterates over *all* fibers × changed keys** — O(fibers × keys) per binding change. *(My note: this is precisely why the machinery must live at configuration granularity and never inside an inner loop.)*
- A provider that has entered `UNLOADING` **stops providing one step before it withdraws**, so dependents recompute an unsatisfied target and tear themselves down while its bindings are still readable.
- **Loader entries:** `id, url, isolate, intercept, config, disabled`, with **per-field dispatch** — `id`/`url` ⇒ rebuild; `isolate` ⇒ realm reassignment (Algorithm 7, using per-key *delimiter* symbols `δₖ` to decide whether a binding is the entry's own); `intercept` ⇒ updated in place, **no reload**; `config` ⇒ handed to the component to diff; `disabled` ⇒ unload/reload. Crucially: **dependencies constrain *when a fiber activates*, not when its module is fetched, so modules load concurrently.**
- **HMR (§5.2.2) needs no developer-annotated accept boundaries** (unlike Webpack/Vite) because a fiber already bounds all of its component's effects. Three phases: module classification to a fixed point (a module is *accepted* if any import is accepted, *declined* if all imports are declined, and anything left undecided inside an import cycle **defaults to declined**); stale-entry detection; transactional reload with cache backup and rollback on import failure.
- **§5.3 Koishi case study.** >4000 community plugins over four years. Koishi currently runs **Cordis v3**; the paper presents **v4**. **Threats to validity, stated by the authors:** a single ecosystem, a single host language, and observational rather than controlled evidence — *"measuring the abstraction's overhead and its effect on developer productivity against a baseline remains future work."*

## 1.8 Discussion (VERIFIED, §6) — the parts that bear on us

- **§6.1 System boundary.** A location is *inside* the boundary only if the system can modify it exclusively **and** restore it; otherwise the operation *"acts as `id_Γ`"* and is neither tracked nor recovered. Two-stage split: **acquisition** (open/malloc/fork install a record inside the boundary — revertible) versus **emission** (write/send push data out — acts as identity). Recovering from an emission needs either withholding (the output-commit problem) or **compensation**, which composes LIFO but for which **the metatheory does not transfer**, since commutation was proved against `≃`.
- **§6.2 Service multiplexing.** Exclusive binding versus a **service broker** that absorbs provider swaps so consumers never reload; enables load balancing, rolling updates, cross-process invocation (which forces an async contract).
- **§6.3 Capabilities.** `inject` is a capability request and the context proxy is a capability mediator; because it is statically declared, the full capability set is known before the component runs. But sandboxing untrusted code needs an **external** execution boundary (SFI, a separate runtime, a sandboxed process, a container) — language-level checks are moot.
- **§6.4 Language independence — directly relevant to Rust.** Temporal composability needs closures plus runtime introduction/retraction of code. Managed runtimes have a module registry; **native code has none, so it needs `dlopen`/`dlclose` or `LoadLibrary`/`FreeLibrary`**; wasm goes either way depending on the embedder (GC'd under a JS host; released when a native embedder such as Wasmtime drops it). Spatial composability needs typed dependency access — and the paper **explicitly names Rust `trait`s/`impl`s** as a way for a provider to extend the context type from its own module, and **Rust procedural macros** as compile-time metaprogramming that *"emits, for each dependency, a typed declaration together with such an accessor, dispensing with a general-purpose interception primitive."* Absent a `Proxy`-like primitive, runtime reflection works *"at the cost of type safety and developer experience."*
- **§6.5 Cycles.** A cycle leaves components permanently inactive, and is **predictable from declarations alone**, so a runtime can report it at load time. Decomposing bidirectional interactions into unidirectional integration components always works in principle but can grow **quadratically** in the number of mutually interacting components; mitigations are package bundling, convention-based wiring, and scaffolding.
- **§6.6 Dependency typing/versioning is an open problem.** Linking is purely **nominal** (by key identity), which yields **interface drift** and **key collision**. Three approaches surveyed: key namespacing (`K × P`); **peer dependencies — what Cordis actually does** — limited by unenforceable semver adherence and single-version resolution; and structural compatibility, undecidable once bounded quantification enters.

## 1.9 Correction to the owner's summary

The owner's summary — *"hot-reloadable, dependency-injected, effect-scoped plugins with automatic disposal"* — is substantively right but **mis-locates the contribution**:

1. **Hot reload is an application (§5.2.2), not the contribution.** It is a corollary of the fiber bounding all of a component's effects.
2. The actual contributions are: **(a)** the algebra — effects as (transform, inverse) pairs forming a monoid under twisted composition, with `track` a monoid *homomorphism*; **(b)** the observational-equivalence quotient that makes **out-of-order, cross-component** revert sound (Cor 21 + Thm 40/42); **(c)** the *reactive* classification of context changes (`notify`: activating / deactivating / neutral); **(d)** an operational semantics with metatheory lifting single-component guarantees to whole-system properties — preservation, progress, and **confluence**.
3. **Finer than stated:** reactivation is triggered by a change in the **identity of the provider** (the committed view `ω`), not merely by a dependency's presence or absence.
4. **"Everything it did is automatically undone" holds only inside the system boundary (§6.1).** Emissions are explicitly outside it, and the metatheory does not cover compensation.
5. The summary omits **isolation realms**, **read-time interception**, and **confluence** — the last of which is, for us, the most valuable idea in the paper.
6. Also worth stating plainly: **the runtime never checks that the inverse is correct.** The guarantee is conditional on author discipline. In Rust, `Drop` gives us a considerably stronger version of the same idea for free.

## 1.10 What transfers to a Rust, compute-heavy, batch application

1. **The `(requires, provides, effect-with-inverse)` component triple as *the* plugin interface.** In Rust this is nearly free: a closure plus a `Drop` guard. It is a better shape than an `init()`/`shutdown()` pair for exactly the reason §1.2.1 gives — locality of concern.
2. **Provision-as-effect** (`set` is itself a revertible effect): registration and deregistration become one code path. This kills the entire class of half-registered-plugin bugs.
3. **The committed view `ω` ⇒ cache invalidation keyed on *provider identity*, not merely presence.** If a different focus-measure plugin now provides `focus.measure`, every derived artefact must be invalidated even though the key is still bound. This is the same idea as LLVM's analysis invalidation, expressed over a dependency graph.
4. **Confluence (Thm 73) as a hard, testable invariant:** the pipeline result must be a function of the declared configuration alone, never of the order in which the user toggled things. This is a property we can property-test.
5. **The commutative-vs-ordered key distinction (p.25).** Our *registries* (focus measures, aligners, decoders) are commutative tables. Our *pixel pipeline* is an ordered chain, and is therefore **not** commutative — so **pipeline order must be explicit data, never an emergent consequence of load order.** RawTherapee bakes it into code; darktable makes it a per-module integer. We should make it data.
6. **Isolation realms** map onto per-frame-group or per-run overrides — e.g. a different camera model for part of a mixed stack — without disturbing the global registry.
7. **Read-time interception** maps onto tuning knobs (tile size, working precision) that must **not** rebuild the pipeline.
8. **Graceful degradation for free.** A component whose coeffect is unavailable stays *inactive* rather than erroring. This is exactly the required semantics for "the camera/lens model plugin is optional".

## 1.11 What breaks — where Cordis's assumptions do not hold for us

1. **The entire cost model is uptime.** Every argument in §1.2 is about long-lived processes: restarts discard caches, unavailability accumulates, in-flight tasks are disrupted. Our process runs for ~30 seconds and exits. Reverting effects in order to *keep the process alive* has near-zero value. **Caveat: the argument returns in full force if we build an interactive GUI or live preview**, which is a plausible v2.
2. **Hot module replacement of native code.** §6.4 concedes that native code needs `dlopen`/`dlclose`. In Rust that means an unstable ABI, and there is no *safe* unloading: dropping a dylib while `Box<dyn Trait>` values originating from it are still alive is undefined behaviour. Cordis's HMR is cheap only because Node has a module registry and a garbage collector.
3. **There is no performance evidence in the paper at all** (explicitly acknowledged in §5.3). Adopting proxied context access, per-access interception merges, and Algorithm 3's O(fibers × keys) notification sweep anywhere near a hot path would be indefensible on the strength of this paper.
4. **"Every interaction passes through this single entity" (§3.3.1) is exactly wrong for 24 GB of pixels.** We want a *fat, direct, typed data path* and a *thin control path*. The paper's own §6.1 licenses this: a location that cannot be reified as a coeffect is simply outside the theorem — so large GPU buffers should live **deliberately** outside the coeffect table.
5. **Interception requires a `Proxy`/property-descriptor mechanism.** §6.4 says the fallback is reflection *"at the cost of type safety."* In Rust: don't. Use proc-macro-generated typed accessors — which the paper itself endorses — and accept static interception only.
6. **Service brokers, rolling updates, cross-process invocation (§6.2) are server concerns.** Irrelevant to a batch job.
7. **Quadratic integration components for mutually-dependent pairs (§6.5)** is a real DX tax that a ~10-plugin image pipeline should not be made to pay.

---

# PART 2 — The Rust plugin design space

## 2.1 Verified crate facts

All from `https://crates.io/api/v1/crates/<name>`, retrieved 2026-08-22. Format: **max stable version**, downloads, last updated. **VERIFIED.**

| Crate | Max stable | Downloads | Updated | Note |
| --- | --- | --- | --- | --- |
| `wasmtime` | 48.0.0 | 32.6 M | 2026-08-20 | newest *published* is 36.0.14 — a patch on the 36.x line released later |
| `libloading` | 0.9.0 | 486.6 M | 2025-11-05 | the baseline `dlopen` wrapper |
| `abi_stable` | 0.11.3 | 3.7 M | **2023-10-12** | **stale — nearly three years without a release** |
| `stabby` | 72.1.16 | 6.0 M | 2026-07-20 | see the Rust-1.78 gotcha below |
| `extism` | 1.30.0 | 643 k | 2026-06-04 | wasm plugin framework |
| `inventory` | 0.3.24 | 117 M | 2026-03-30 | static registration |
| `linkme` | 0.3.37 | 29.3 M | 2026-07-18 | static distributed slices |
| `wgpu` | 30.0.1 | — | 2026-08-22 | |
| `naga` | 30.0.1 | — | 2026-08-22 | lockstep with wgpu |
| `naga_oil` | 0.23.0 | 6.0 M | 2026-07-14 | "combining and manipulating shaders using naga IR" |
| `wesl` | 0.4.3 | 262 k | 2026-08-14 | |
| `rhai` | 1.25.1 | — | — | |
| `mlua` | 0.12.0 | — | — | |
| `starlark` | 0.14.2 | — | — | |
| `wasmer` | 7.3.0 | — | — | |
| `wit-bindgen` | 0.60.0 | — | — | |
| `nu-plugin` | 0.115.0 | — | — | |
| `bevy` | 0.19.1 | — | — | |
| `cudarc` | 0.19.9 | — | — | maintained CUDA bindings |
| `cust` | 0.3.2 | — | **2022** | stale |
| `krnl` | 0.1.1 | — | **2024** | stale |
| `rawler` | 0.7.2 | — | — | Rust raw decoding |
| `rayon` | 1.12.0 | — | — | |
| `spirv-tools` | 0.13.3 | — | — | |
| `rspirv` | 0.13.0+sdk-1.4.341.0 | — | — | |
| `spirv-builder` | 0.9.0 | — | — | rust-gpu |
| `slang-rs` | 0.22.0 | 645 k | 2026-08-07 | |
| `shader-slang` | 0.1.0 | 8 k | 2025-07-23 | |
| `iceoryx2` | 0.9.3 | — | — | "Lock-Free Zero-Copy Interprocess Communication" |
| `safer-ffi` | 0.1.13 | — | — | |
| `arrow` | 59.2.0 | — | — | |
| `image` | 0.25.10 | — | — | |

## 2.2 Option 1 — compile-time / trait-object plugins

A registry of `Box<dyn Stage>`, populated either explicitly or by static registration (`inventory` 0.3.24, `linkme` 0.3.37 — both actively maintained and very widely used), with feature flags for optional stages and generic monomorphization where a stage is hot enough to warrant it.

- **Cost:** effectively zero. A `dyn` call is one indirect branch, amortized to nothing when the callee processes a whole tile.
- **Downside:** "contributable by others" means "fork, add a crate, recompile". For a scientific/photographic tool distributed as a binary, that is a real barrier — but a *much smaller* one than it appears, because the contributions we actually expect (a new focus measure, a lens profile) do **not** need native code (see §2.7 and Part 4).

## 2.3 Option 2 — dynamic libraries

`libloading` 0.9.0 (486.6 M downloads) gives you `dlopen`. The problem is that **Rust has no stable ABI**, so anything crossing the boundary must be `#[repr(C)]`, and both sides must be built with the same compiler.

- **`abi_stable` 0.11.3** — last released **2023-10-12**. **VERIFIED stale.** Depending on it in 2026 for a new project is a maintenance risk.
- **`stabby` 72.1.16** — actively maintained, but **docs.rs failed to build 72.1.16** (VERIFIED from the docs.rs page), and its README carries an explicit warning: because of a breaking change in **Rust 1.78**, trait-object v-tables are inserted into a global lock-free **leaked** set, lookup is an **O(n) linear search**, and insertion clones the vector; *"if your project uses many stabby-defined trait objects, I suggest using either nightly or a < 1.78 version of the compiler."* It also notes that `#[repr(stabby)]` enums lose pattern-matching and hurt compile times. **This is disqualifying for a project that wants many trait objects on a hot path.**
- **Bevy's `dynamic_linking` feature is *not* a plugin ABI.** VERIFIED from Bevy's `cargo_features.md`: `dynamic_linking` = *"Force dynamic linking, which improves iterative compile times"* — a **developer compile-speed** feature. Citing Bevy as evidence that Rust dylib plugins work in production would be a misreading.
- **LLVM does do this successfully** (`opt -load-pass-plugin=path/to/plugin.so`, VERIFIED from `llvm.org/docs/NewPassManager.html`) — but LLVM is C++ with a stable-enough in-tree ABI and plugins built against the same LLVM.
- **darktable does this successfully too**, via GModule `dlopen` of C modules with a `#[repr(C)]`-equivalent v-table (VERIFIED from `src/develop/imageop.h`). Note the language: **C**, not C++ or Rust.

**Verdict:** a `#[repr(C)]` v-table with a leading version word is the only defensible dynamic-library design in Rust, and it is a seam to *reserve*, not to build now.

## 2.4 Option 3 — WebAssembly / the Component Model

This is the fashionable answer and it is the **runner-up**, but it loses on four verified facts.

1. **The Canonical ABI is a copy boundary, by design.** VERIFIED from the Component Model's Canonical ABI explainer: *"While the Python code for lifting and lowering values appears to create an intermediate copy… a real implementation should be able to fuse lifting and lowering into a single direct copy from the source linear memory into the destination linear memory."* The best case is **one copy**, not zero.
2. **Wasmtime's proposal support** (VERIFIED from the **raw** `docs/stability-wasm-proposals.md`; the rendered mdBook page strips the tables):
   - **Tier 1, fully supported:** `simd`, **`relaxed-simd`**, **`memory64`**, `multi-memory`, `tail-call`, `gc`, `exception-handling`, `wide-arithmetic`. So SIMD *is* usable and >4 GiB linear memories *are* available.
   - **`component-model` is Tier 1 and enabled by default in Wasmtime, but is NOT at phase 4** of standardization; fuzzing is 🚧 and the C API has gaps.
   - **`threads` is Tier 2**, with `Finished: 🚧` and `Fuzzed: ❌`, known issues around shared memories, and **shared memories are not supported in the pooling allocator**.
   - **Unimplemented:** `shared-everything-threads`, `memory-control`, `flexible-vectors`, `compact-import-section`.
3. **A wasm plugin cannot portably drive the GPU today.** `wasi-webgpu` is at **Phase 2** (VERIFIED from the repo). It is explicitly scoped to bring GPU compute to wasm, but it is nowhere near shippable.
4. **The scale mismatch.** *Derived arithmetic, not a fetched benchmark — labelled as such:* 33 MP × 4 channels × 4 bytes ≈ **528 MB per frame**; × 40 frames ≈ **21 GB**. One full copy at ~20 GB/s is roughly **1 second per pass**. Our unit of work is half a gigabyte, not four kilobytes.

**Verdict:** wasm is a *correct* answer for small, untrusted, control-plane extensions and a *wrong* answer for a stage that must touch the working set. Note the asymmetry, though: the *combination* — wasm for parameter logic, native for pixels — is not obviously wrong, and `memory64` + `relaxed-simd` being Tier 1 means the door is not closed forever. It is closed for 2026.

## 2.5 Option 4 — out-of-process / IPC

The best-documented production example is **nushell** (VERIFIED from the plugin protocol reference):

- Plugins are executables named `nu_plugin_*`.
- **stdio mode is mandatory**; **local-socket mode is optional** (Unix domain socket / Windows named pipe), advertised via a `LocalSocket` feature, using **two separate connections** — input then output — so separate threads can own each direction.
- Encoding is announced as a length-prefixed string: `"\x04json"` or `"\x07msgpack"`.
- A mandatory `Hello` handshake carries `protocol`/`version`/`features` and must be semver-compatible or the engine disconnects.
- `Call`/`CallResponse` are keyed by ID; there are stream messages, engine calls (plugin → engine), an asynchronous `Signal` (e.g. Interrupt), and `Goodbye`.

This is a genuinely good protocol design and worth copying *structurally* (versioned handshake, ID-keyed calls, streams, out-of-band interrupt). But for pixel data it means either a copy or shared memory. `iceoryx2` 0.9.3 ("Lock-Free Zero-Copy Interprocess Communication") solves the shared-memory part for host RAM — but **not** for GPU memory, and process isolation is precisely what makes GPU resource sharing hard.

**Verdict:** correct for untrusted or crash-prone plugins (a proprietary RAW decoder, say). Wrong as the default.

## 2.6 Option 5 — scripting / declarative composition

The insight here is that we can separate the two things "pluggable" is being asked to mean:

- **New algorithms** → need native (or GPU) code.
- **New *compositions* of existing algorithms** → need only data.

The second is far more common, and **FFmpeg proves it at scale**: a filtergraph is a *string* (VERIFIED from `ffmpeg-filters.html` — filters have multiple in/out **pads**; the graph may contain cycles and multiple links per pair; filters within a chain are separated by `,`, chains by `;`; link labels go in `[brackets]`; the syntax is `[in1]…filter_name@id=args[out1]…`; args are `:`-separated `key=value` or positional; list values are separated by `|`; an unlabelled output links to the next filter's first unlabelled input). Millions of users compose FFmpeg pipelines without ever compiling anything.

For scripting proper, the live options are `rhai` 1.25.1 (pure Rust, sandboxable), `mlua` 0.12.0 (LuaJIT-capable), `starlark` 0.14.2 (deterministic, hermetic — the Bazel/Buck configuration language, which is *precisely* the right semantics for a reproducible pipeline description). A declarative graph in RON/TOML is the same idea with less rope.

**Verdict:** adopt the declarative graph. Defer the scripting language until someone needs conditionals.

## 2.7 Option 6 — the kernel-contribution problem (the crux)

A stacking-algorithm plugin will want to run on the GPU. If the plugin boundary is a *binary* boundary, we must ship compiled pipelines across it, and every ABI problem returns in a worse form. **The way out is to make the plugin boundary a *source* boundary at the shader level.**

### 2.7.1 `naga_oil` — already a shader plugin system, already in production (VERIFIED, GitHub README)

`naga_oil` 0.23.0 is what Bevy uses. From its README:

- Modules are named with `#define_import_path`; imports are `#import my_module;`, `#import mod as alias`, `#import my_module::{a, b}`, and nested Rust-style paths.
- **Each module is built independently to naga IR**, with per-language "header" files, and final shaders are made by **combining IR** — *"for multiple small shaders with large common imports, this can be faster than parsing the full source for each shader."*
- **`virtual fn` + `override fn Module::name(...)`** — an override replaces **all** calls to the original throughout the entire shader scope (except calls made inside the override itself), so overrides form a **stack ordered by first occurrence in a depth-first search of the import tree**, and multiple overrides chain (c overrides b overrides a). Signatures must match.
- **Constraints (important):** overrides can currently only be defined **in WGSL**, and must be declared in the top-level shader or imported as an `additional_import` — a plain `#import` will not work, because of tree-shaking.
- Conditional compilation via `shader_def` string/value pairs (`Bool`/`Int`/`UInt`) with `#ifdef`/`#ifndef`/`#if op value`/`#else if`/`#endif`, plus `#SHADER_DEF` / `#{SHADER_DEF}` substitution and `#define`.
- Modules may be **GLSL or WGSL**. A `prune` module strips dead code and bindings. `Composer::non_validating()` disables error-reporting quality.

**This is exactly the mechanism we need, and it already ships in a major Rust project.**

### 2.7.2 WESL — the standards-track alternative (VERIFIED, `wesl-lang.dev`)

`wesl` 0.4.3 is a **strict superset of WGSL** adding imports, conditional compilation, and **packages shared on npm and cargo**. Linkers exist in both Rust and JS (<20 kb), and there is an ecosystem: `wgsl-test` (with `@test`), `wgsl-studio`, `wgsl-analyzer`. Where `naga_oil` is an ad-hoc preprocessor over naga IR, WESL is trying to be a language-level standard **with a package ecosystem** — which is precisely the "contributable by others" property we want. It is younger (262 k downloads vs 6.0 M).

### 2.7.3 Slang — the strongest technical answer (VERIFIED, Slang user guide)

Slang provides, in a shading language, the abstractions we would otherwise have to invent:

- **Interfaces and generics:** `interface IFoo {...}`, `struct MyType : IFoo`, default methods, `override`, properties, static methods, **static constants**, and the `This` type. Generics take `where T : IFoo` constraints and are **structurally type-checked once** — they are *not* C++ templates. Generic **value** parameters (`<let n : int>`) may be used in attributes, e.g. `[numthreads(blockSize, blockSize, 1)] void computeMain<int blockSize>()`.
- **Link-time specialization** (its own documentation page) — a three-step model: precompile modules to binary IR (`slangc main.slang -o main.slang-module`), **link**, then generate target code. Specialization arguments (constants **or types**) are supplied **at link time**, reusing all front-end work. Examples: `extern static const int kSampleCount;` resolved by another module's `export static const int kSampleCount = 2;`; and `extern struct Sampler : ISampler;` resolved by `export struct Sampler : ISampler = FooSampler;`. Also available through the C++/COM API (`loadModule`, `loadModuleFromSourceString`, `createCompositeComponentType`, `link`, `getEntryPointCode`).
- The documentation's stated motivation is **exactly our problem**: preprocessor-based specialization forces the compiler to redo parsing, type-checking, IR generation and optimization for every variant.
- **Targets** include SPIR-V, HLSL, CUDA and Metal, across rasterization, compute and ray-tracing pipelines.

That target list is the key fact: **Slang can emit both SPIR-V (for the wgpu/Vulkan baseline) and CUDA (for the fast path) from one source.** Rust bindings: `slang-rs` 0.22.0 (645 k downloads, updated 2026-08-07) and `shader-slang` 0.1.0 (8 k, 2025-07-23 — immature).

### 2.7.4 The prior art in real image pipelines

**darktable's per-module OpenCL variant** is the closest analogue in a shipping raw processor: `process_cl` is **OPTIONAL** per module, and the framework falls back to the CPU `process` when it is absent (VERIFIED from `src/iop/iop_api.h`). That is precisely the "GPU support is optional per plugin" shape we want.

**Halide** (VERIFIED, halide-lang.org) gives the deeper idea — the **algorithm/schedule split**: `blur_x(x,y) = (input(x-1,y)+input(x,y)+input(x+1,y))/3;` is *"the algorithm — no storage or order"*, and `blur_y.tile(x,y,xi,yi,256,32).vectorize(xi,8).parallel(y); blur_x.compute_at(blur_y, x).vectorize(x,8);` is *"the schedule — defines order, locality; implies storage"*. GPU targets include CUDA, OpenCL, OpenGL compute, Metal and DX12, and autoschedulers exist. **This maps directly onto our plugin split: the plugin declares *what* it computes; the framework decides *how* it is tiled and scheduled.**

**Exo** (VERIFIED, github.com/exo-lang/exo) is Python-embedded and user-schedulable, with `exocc` emitting `.c`/`.h`; it depends on PySMT + Z3/CVC4 and CMake ≥3.21 + Ninja. **It is an offline code generator with a Python build step, not a runtime** — usable to author one hand-tuned kernel, not usable as a plugin format.

### 2.7.5 CUDA ↔ Vulkan zero-copy (VERIFIED, NVIDIA CUDA Runtime API, "External Resource Interoperability")

The optional CUDA fast path can share buffers with the wgpu/Vulkan baseline **without a copy** via `cudaImportExternalMemory` and `cudaImportExternalSemaphore`. `cudaExternalSemaphoreHandleType` values include `OpaqueFd` (1), `OpaqueWin32` (2), `OpaqueWin32Kmt` (3), `D3D12Fence` (4), `D3D11Fence` (5), `NvSciSync` (6), `KeyedMutex` (7/8), `TimelineSemaphoreFd` (9), `TimelineSemaphoreWin32` (10).

**Ownership gotcha, verified and easy to get wrong:** for `OpaqueFd`, **ownership of the file descriptor transfers to the CUDA driver**; for `OpaqueWin32`, ownership is **not** transferred and the application must release the handle itself. Since the dev machine is Windows 11 + WSL2, both paths matter.

**UNVERIFIED:** whether `wgpu` 30 exposes the raw Vulkan `VkDeviceMemory` handle needed to feed `cudaImportExternalMemory`. My attempt to fetch the `wgpu::Device::as_hal` documentation returned only the error-scope section. Bevy's `raw_vulkan_init` feature (*"Forces the wgpu instance to be initialized using the raw Vulkan HAL, enabling additional configuration"*, VERIFIED from `cargo_features.md`) is strongly suggestive that a HAL escape hatch exists, but **this must be confirmed before the CUDA fast path is committed to.** It is the single highest-value open question in this workstream.

Also VERIFIED from Bevy's `cargo_features.md`: `hotpatching` (*"Enable hotpatching of Bevy systems"*), `shader_format_spirv`, and **`spirv_shader_passthrough`** (*"Only supported on Vulkan, shader capabilities and extensions must agree with the platform implementation"*) — the last being the route by which a plugin could ship precompiled SPIR-V instead of WGSL source.

---

# PART 3 — Prior art in pluggable image pipelines

## 3.1 darktable — the richest source (VERIFIED from `src/develop/imageop.h` and `src/iop/iop_api.h`)

darktable is twenty years of hard-won experience in exactly our problem domain, and its module header is the most valuable single document I read for Part 3.

- **Loading:** modules are `dlopen`ed via GModule (`dt_iop_load_modules_so` / `dt_iop_unload_modules_so`); `dt_iop_module_so_t` caches the dlopen'd v-table.
- **API declaration:** `iop_api.h` declares the interface with `REQUIRED(...)` / `DEFAULT(...)` / `OPTIONAL(...)` macros, and the header is **included twice** (with and without `FULL_API_H`) to generate both the struct and the type-checked declarations. A C idiom whose Rust equivalent is a trait with required methods and provided defaults — we get this for free.
- **Two-pass ROI negotiation — steal this outright:**
  - `modify_roi_out(self, piece, roi_out, roi_in)` — **first pass, traversing first→last**: "how large would the output be, given this input ROI?" (used by `dt_dev_pixelpipe_get_dimensions`).
  - `modify_roi_in(self, piece, roi_out, roi_in)` — **second pass, traversing last→first**: "which ROI would this operation need as input to fill the given output region?" The header comment notes that **the tiling code also uses this to compute a tile's ROI**.
- **`tiling_callback(self, piece, roi_in, roi_out, tiling)`** — *"report back info for tiling: memory usage and overlap. **Memory usage: factor \* input_size + overhead**."* **A module declares its own memory model so the framework can decide how to tile.** With 24 GB working sets this is not optional for us.
- **Format and colourspace negotiation:** `input_format` / `output_format` (filling a `dt_iop_buffer_dsc_t`), `default_colorspace` (**REQUIRED**), `input_colorspace`, `output_colorspace`, `blend_colorspace`.
- **Four process entry points:** `process` (**REQUIRED**; the comment warns *"you can only use OpenMP SIMD here, no intrinsics"*), `process_tiling` (DEFAULT), `process_cl` (**OPTIONAL**, taking `cl_mem dev_in/dev_out` and returning a CL error code), `process_tiling_cl` (DEFAULT).
- **Capability flags (`dt_iop_flags_t`):** `ALLOW_TILING`, `TILING_FULL_ROI` (*"tiling code has to expect arbitrary roi's… incl. flipping, mirroring"*), **`FENCE` (*"No module can be moved pass this one"*)**, `ONE_INSTANCE`, `PREVIEW_NON_OPENCL`, `EXPAND_ROI_IN`, `WRITE_DETAILS`, `WRITE_RASTER`, `WRITE_PIPECACHE`, `WRITE_PIPECACHE_IN`, `SUPPORTS_BLENDING`, `NO_MASKS`, `DEPRECATED`, `ALLOW_FAST_PIPE`, `UNSAFE_COPY`.
- **Versioning and migration:** `legacy_params(self, old_params, old_version, new_params, new_params_size, new_version)` plus `dt_iop_legacy_params(...)`. Params are a raw struct plus `params_size`. **Twenty years of experience says: build the migration hook on day one.**
- **Introspection:** `DT_MODULE_INTROSPECTION()` auto-implements `introspection_init`, `get_introspection`, `get_introspection_linear`, `get_p(param, name)`, `get_f(name)`, with a `have_introspection` flag. This is reflection over a C struct via a code generator — in Rust, `serde` + `schemars`, or a proc macro.
- **Ordering is data:** `iop_order` (an int — *"the pipe will be sorted by iop_order"*) and `position`; multiple instances via `multi_priority` / `multi_name` / `instance`.
- **Geometry as a capability:** `distort_transform` / `distort_backtransform` (arrays of `{x1,y1,x2,y2,…}`) / `distort_mask`. A warping module must map points **both ways** — exactly what a focus-breathing or scale-alignment plugin needs so that masks and control points follow the warp.
- **Raster masks are a side-channel product graph:** `raster_mask.source.users` (module→id) and `.masks` (id→name), `IOP_FLAGS_WRITE_RASTER`, `dt_iop_advertise_rastermask`; `dt_iop_commit_blend_params` will *"invalidate the source's cachelines onward so it re-runs and writes one"* if a requested mask isn't stored. **This is a direct analogue of our focus maps**, which are produced by one stage and consumed by another out of band from the main pixel path.

## 3.2 RawTherapee — the instructive counterexample (VERIFIED, RawPedia "Toolchain Pipeline")

RawTherapee has a **fixed, hard-coded order**: preprocess (dark frame, flat field, bad/hot pixels, scale colors, raw black point, lens distortion, green equilibration, line noise, CA, raw white point) → demosaic → retinex → highlight recovery → white balance → spot removal → crop → convert colorspace → NR → dehaze → DRC → … → resize → post-resize sharpening → final Lab→RGB. Four separate pipelines exist (main preview, saved image, thumbnail, and one more).

There is no per-module negotiation and no plugin surface. It is a perfectly good raw processor. **The lesson is that a fixed pipeline is a viable product** — which should temper our enthusiasm — but also that adding a stage means editing the pipeline in four places.

## 3.3 libvips — demand-driven streaming (VERIFIED, `how-it-works.html`)

- **Regions:** `vips_region_new` / `vips_region_prepare(region, &rect)` / `VIPS_REGION_ADDR(region, x, y)`.
- A *partial image* stores a **start / generate / stop** triple instead of pixels; *"a start / generate / generate / stop sequence works like a thread"*; start and stop are mutually exclusive and a state is never used by more than one `generate`. Joining operations is a single function call.
- **Operations must be side-effect free, and are therefore cacheable: libvips caches the last 100 operation calls, keyed on operation plus arguments.** Side-effecting operations (e.g. `vips_draw_circle`) emit an **"invalidate" signal** that makes all downstream operations and caches drop their contents.
- **Tile hints:** operations tell sinks their preferred tile geometry.
- **Four lock operations per output tile, regardless of pipeline length or complexity**; intermediates are small enough to fit in L2.
- SIMD via **Google Highway** with runtime dispatch, *"typically speeds operations up by a factor of three or four."*

**What to steal:** purity as the precondition for caching; the invalidate signal; tile hints negotiated rather than imposed; and the discipline that pipeline length should not increase synchronization cost.

## 3.4 GStreamer — caps negotiation (VERIFIED; note the docs site 503'd twice, so I read the raw markdown at `gitlab.freedesktop.org/gstreamer/gstreamer/-/raw/main/subprojects/gst-docs/markdown/additional/design/negotiation.md`)

Two rules govern everything: **(1) downstream suggests formats; (2) upstream decides on the format.**

Four mechanisms:
- `GST_QUERY_CAPS` — get possible formats; works **recursively**; takes a `filter` whose *order* expresses caller preference.
- `GST_QUERY_ACCEPT_CAPS` — check a **fixed** caps; need not recurse.
- `GST_EVENT_CAPS` — configure; travels downstream; must be fixed.
- `GST_EVENT_RECONFIGURE` — inform upstream that caps may have changed.

The canonical loop is: query own caps → peer-query filtered by them → fixate each candidate → `peer_accept_caps` → push a CAPS event.

**And the zero-copy hook: the `ALLOCATION` query negotiates the allocator and buffer pool.** That is the piece most people forget — format negotiation and *memory* negotiation are separate queries.

## 3.5 FFmpeg — composition as a string (VERIFIED, `ffmpeg-filters.html`)

Covered in §2.6. The takeaway: **the most widely-used image/video pipeline in the world is configured by a string, and its algorithms are plain C.** "Pluggable" for the overwhelming majority of users means "recomposable", not "loadable".

## 3.6 Bevy — the leading Rust example (VERIFIED, docs.rs `Plugin` trait + `cargo_features.md`)

```rust
pub trait Plugin: Downcast + Any + Send + Sync {
    fn build(&self, app: &mut App);
    fn ready(&self, _: &App) -> bool;
    fn finish(&self, _: &mut App);
    fn cleanup(&self, _: &mut App);
    fn name(&self) -> &str;
    fn is_unique(&self) -> bool;
}
```

Most plugins are simply `fn(&mut App)`. Uniqueness is enforced by `name()`, which defaults to the type name.

**The instructive detail:** `finish` exists *precisely* for **"plugins that depend on another plugin's asynchronous setup, like the renderer"**. That is a hand-rolled, weaker version of Cordis's coeffect ordering — Bevy needed exactly the property Cordis formalizes, and solved it with an extra lifecycle phase. This is good evidence that the coeffect idea is real and not academic.

Note again that `dynamic_linking` is a **compile-time** feature, not a plugin ABI (§2.3).

**UNVERIFIED:** Bevy's **render graph**. Both docs.rs URLs I tried 404'd (`bevy_render::render_graph`, `bevy::render::render_graph`). I therefore make **no claims** about its node/slot API.

## 3.7 LLVM's new pass manager — the invalidation model (VERIFIED, `llvm.org/docs/NewPassManager.html`)

- IR hierarchy Module → (CGSCC →) Function → Loop, with a `PassManager` **and an `AnalysisManager` per level**, plus adaptors (`createFunctionToLoopPassAdaptor`, `createModuleToFunctionPassAdaptor`, `createModuleToPostOrderCGSCCPassAdaptor`).
- **Analysis caching:** querying an analysis checks whether a result was already computed **and is still valid**; otherwise it runs `run()`, caches, and returns. `getCachedResult` returns a result only if it is already cached.
- Cross-level access goes through proxies (`FunctionAnalysisManagerCGSCCProxy`, `ModuleAnalysisManagerCGSCCProxy`).
- Analysis managers **must be declared in a specific order** so that they are destroyed correctly, because of inter-manager references.
- **Extension points:** `PB.registerPipelineStartEPCallback([](ModulePassManager &MPM, OptimizationLevel){ MPM.addPass(FooPass()); })` lets frontends and backends inject passes into the default pipelines; `TargetMachine::registerPassBuilderCallbacks()`; and **`opt -load-pass-plugin=path/to/plugin.so`** loads a dynamic pass plugin.
- Grouping passes of the same level into one manager is better for cache locality **and can change optimization quality**.

**What to steal:** the analysis-vs-transform distinction (our *analyses* are aligned frames, focus pyramids, noise estimates; our *transforms* are the merge), explicit validity/invalidation rather than ad-hoc flags, and the extension-point pattern for injecting stages into a default pipeline without forking it.

## 3.8 Nix — content-addressed derivations (VERIFIED, raw `doc/manual/source/store/derivation/index.md` from NixOS/nix)

A **derivation** is *"a specification for running an executable on precisely defined input to produce one or more store objects"*, consisting of: a name; an **inputs specification** (a set of deriving paths); an **outputs specification**; a **system** type (which is what enables heterogeneous build plans); and process-creation fields (*"everything needed for an `execve`"*). Derivations are referred to by the store path of the store object that encodes them (the "derivation path").

**Deriving paths** are either *constant* (a store path) or *output* (a drvPath plus an output name) — this second form is needed because *"for content-addressing derivations, the store path of an output is not known in advance."*

**The critical discipline, quoted because it is the whole lesson:** *"rather than somehow scanning all the other fields for inputs, Nix requires that **all inputs be explicitly collected in the inputs field**."*

For us: **a stage that reads an input it did not declare silently corrupts the cache.** Declaration must be mandatory and, ideally, enforced by construction (the stage can only reach inputs handed to it).

The `system` field is also directly relevant: our cache key must include device and precision, because a CUDA-computed alignment and a wgpu-computed alignment are not necessarily bit-identical artefacts.

## 3.9 Lensfun — correction ordering, and why it is worth copying verbatim (VERIFIED, `lensfun.github.io/manual/latest/corrections.html`)

Lens corrections are **not commutative**. Lensfun's *conceptual* order is:

1. devignetting, 2. anti-TCA, 3. undistortion, 4. change of projection, 5. perspective correction, 6. scaling.

The stated rationale: vignetting and TCA are both measured on the pristine image; very heavy TCA would corrupt a vignetting measurement far more than heavy vignetting would corrupt a TCA measurement — so **devignetting must come first**.

**But the actual implementation runs the coordinate transforms in reverse** — scaling → perspective → projection → undistortion → anti-TCA — because you start from the (empty) rectified output image and *distort its coordinates* to look up into the source RAW, which needs only **one interpolation and one pixel lookup** for TCA and distortion combined. This is why `lfDistortionModel` and `lfTCAModel` map **undistorted → distorted**. Devignetting is still applied first and separately, via `lfModifier::ApplyColorModification`; the geometric part goes through `lfModifier::ApplySubpixelGeometryDistortion`.

Projection formulas, for reference: equisolid `r = 2f·sin(θ/2)`; equidistant `r = f·θ`; stereographic `r = 2f·tan(θ/2)`; orthographic `r = f·sin(θ)`; rectilinear `r = f·tan(θ)`.

**Do not re-derive this. Copy the ordering and the inverse-mapping convention.** It is also a perfect concrete instance of Cordis's ordered-vs-commutative key distinction: the lens-correction chain is an **ordered chain**, so its order must be fixed by the framework, not left to plugin load order.

---

# PART 4 — The recommendation

## 4.1 The mechanism

> **Statically-linked Rust trait-object stages, registered through a Cordis-shaped `Context` (`requires` → `provides` → one effect closure returning a disposer), composed by a declarative pipeline graph in RON/TOML, with GPU kernels contributed as source-level WGSL modules composed by `naga_oil` (`virtual`/`override`) — optionally precompiled SPIR-V, and optionally authored once in Slang to emit both SPIR-V and CUDA.**

**Runner-up: the Wasm Component Model on wasmtime.** It lost on three verified facts (§2.4): the Canonical ABI is a **copy** boundary by explicit design; `shared-everything-threads` and `memory-control` are **unimplemented** in Wasmtime while `threads` is Tier 2 with shared memories unsupported in the pooling allocator; and `wasi-webgpu` is only at **Phase 2**, so a wasm plugin cannot drive the GPU. Our unit of work is ~528 MB per frame, not 4 KB. Wasm is the right answer for a *control-plane* extension and the wrong answer for a pixel stage — in 2026.

## 4.2 The central insight

**Partition plugin kinds by what a plugin actually needs to contribute.** This dissolves both the ABI problem and the GPU problem at once.

- Most of the plugin surface — **camera models, lens models, focus measures, merge weighting functions, tone curves** — is **data plus a GPU kernel source**. That needs **no ABI at all**. It is hot-reloadable for free (re-read a file, recompose the shader, rebuild the pipeline), sandboxed for free (a shader cannot scribble on our heap), and portable for free.
- Only genuinely *algorithmic* plugins (a new global aligner, a new pyramid construction, a new RAW decoder) need native code — and there are very few of them, they are the ones most likely to live in-tree anyway, and they are exactly the ones for which "fork and recompile" is an acceptable price.

Almost every plugin system that hurts, hurts because it tried to make one mechanism serve both cases.

## 4.3 Plugin kinds

| Kind | Contributes | Native code? | GPU? |
| --- | --- | --- | --- |
| `RawDecoder` | bytes → Bayer + metadata | yes | no |
| `Preprocess` | black/white level, PDAF repair, CFA-domain denoise | usually | yes |
| `Aligner` | frame → frame warp field / homography / dense flow | yes | yes |
| `FocusMeasure` | tile → per-pixel sharpness scalar | **no — kernel body only** | yes |
| `Merger` | (frames, focus maps) → merged frame | sometimes | yes |
| `Postprocess` | halo suppression, denoise, sharpening | sometimes | yes |
| `Writer` | merged frame → TIFF/EXR/JPEG-XL | yes | no |
| `CameraModel` | **data only** | **no** | n/a |
| `LensModel` | **data only** | **no** | n/a |

The two most-contributed kinds — `FocusMeasure` and the camera/lens models — need **no native code whatsoever**. That is the whole design in one sentence.

## 4.4 The data model, and zero-copy

**Plugins never own buffers. The framework's arena/pool does.** What crosses the plugin boundary is a **descriptor** of tens of bytes, plus a bind group or a device pointer:

```rust
struct TileView {
    storage: Storage,        // Host(&[T]) | Device(wgpu::Buffer + offset) | Cuda(DevicePtr)
    strides: Strides,
    domain: Domain,
    device: DeviceClass,     // Cpu | Wgpu | Cuda
    precision: Precision,    // F16 | F32 | U16
}

enum Domain {
    Bayer { cfa: CfaPattern, black: [u16; 4], white: [u16; 4] },
    LinearRgb { primaries: Primaries },
    Scalar { semantic: ScalarSemantic },   // focus map, weight, depth, confidence
}
```

Because everything is in-process and statically linked, `&[f32]` and `wgpu::Buffer` cross the boundary **directly**. There is no marshalling, no lifting/lowering, no serialization. **This is the single reason the mechanism in §4.1 wins**: a design that is otherwise merely conservative becomes strictly dominant the moment the payload is half a gigabyte.

GPU↔GPU zero-copy across the wgpu/CUDA seam uses `cudaImportExternalMemory` + `cudaImportExternalSemaphore` (§2.7.5), subject to the **UNVERIFIED** question of whether wgpu 30 exposes the underlying `VkDeviceMemory`.

## 4.5 The `Stage` trait — capabilities and negotiation

Steal darktable's two-pass ROI negotiation and memory declaration, and GStreamer's "downstream suggests, upstream decides":

```rust
trait Stage: Send + Sync {
    fn caps(&self) -> Caps;                                       // domains in/out, device classes, precisions
    fn negotiate(&self, downstream: &Caps) -> Result<Agreed>;     // GStreamer rule 2
    fn roi_out(&self, roi_in: Roi) -> Roi;                        // darktable modify_roi_out (first -> last)
    fn roi_in(&self, roi_out: Roi) -> Roi;                        // darktable modify_roi_in (last -> first)
    fn resources(&self, roi_in: Roi, roi_out: Roi) -> Resources;  // { factor, overhead, halo, access }
    fn run(&self, ctx: &RunCtx, inputs: &[TileView], outputs: &mut [TileViewMut]) -> Result<()>;
}

enum Access {
    Streaming { halo: u32 },   // can be tiled; needs halo pixels of context
    WholeFrame,                // needs a whole frame resident
    WholeStack,                // needs all N frames resident simultaneously
}
```

`Resources { factor, overhead, ... }` is darktable's `tiling_callback` verbatim (*"factor \* input_size + overhead"*).

**`Access` is the single most important capability for us.** It is what decides whether 24 GB can be streamed in tiles or must be resident — and it is the difference between a tool that works on 64 GB and one that thrashes. A `WholeStack` stage in the middle of an otherwise streamable pipeline is a scheduling catastrophe the framework must be able to *see* before it runs anything.

Memory negotiation is separate from format negotiation (GStreamer's `ALLOCATION` query): stages request buffers from the framework's pool; they never allocate.

## 4.6 The GPU-kernel-contribution answer

**The framework owns the *schedule*; the plugin owns the *algorithm*.** This is Halide's split, implemented with `naga_oil`'s `virtual`/`override`.

The framework declares, in a core WGSL module:

```wgsl
// core::focus
virtual fn measure(t: TileView, x: u32, y: u32) -> f32 { /* default: Laplacian variance */ }
```

A focus-measure plugin ships:

```wgsl
#import core::focus
override fn core::focus::measure(t: TileView, x: u32, y: u32) -> f32 { /* Sobel-Tenengrad, etc. */ }
```

`naga_oil` composes the core dispatch shell + the plugin's override + `shader_defs` (tile size, channel count, precision) into a single `naga::Module`, which becomes one `wgpu` pipeline. **VERIFIED that `naga_oil` supports exactly this**, including override chaining ordered by depth-first import order (§2.7.1) — with the constraint that overrides must be WGSL and must be top-level or `additional_import`ed.

Consequences:

- **Plugins do not create pipelines, allocate device memory, or submit command buffers.** They contribute kernel bodies and a parameter schema. The framework decides workgroup size, tiling, buffer layout, and submission — which is also what makes it possible to *change* those decisions later without breaking every plugin.
- **A single dispatch, not a dispatch per plugin.** Because the override is spliced in at compile time, there is no indirect call, no kernel-launch overhead per plugin, and no intermediate buffer. **The plugin boundary costs literally zero at runtime** — which is the requirement the owner set.
- **The CUDA fast path** either ships a separate `.cu`/PTX alongside the WGSL, or — better — the kernel is authored once in **Slang** and emitted to both SPIR-V and CUDA via link-time specialization (§2.7.3). Slang's `extern`/`export` link-time specialization is a *cleaner* mechanism than `naga_oil`'s override stack and is the natural v2 migration if the WGSL-only constraint bites.
- **CPU fallback** is a plain Rust `fn` with the same signature, selected when no GPU is available. Following darktable, the GPU path is **optional per stage** and the framework falls back (`process_cl` is `OPTIONAL` in `iop_api.h`).
- **WESL** (§2.7.2) is the standards-track escape hatch if a real package ecosystem for shader plugins becomes desirable — it already has cargo/npm package distribution, which `naga_oil` does not.

## 4.7 Camera and lens model plugins — data, and graceful degradation

A `CameraModel` contributes: CFA layout; per-ISO black and white levels; a PDAF pixel coordinate map; a noise model (σ² = a·x + b); colour matrices. A `LensModel` contributes: distortion / TCA / vignetting polynomial coefficients keyed by (focal length, aperture, focus distance) — **using lensfun's models and, critically, lensfun's ordering constraint verbatim** (§3.9); a focus-breathing magnification-vs-focus-position curve; and a focus-position → subject-distance mapping.

Focus breathing is where this pays off most: a macro stack shot by racking focus changes magnification frame to frame, and knowing the breathing curve turns a hard registration problem into a near-closed-form pre-scale.

**Mechanism:** these are provided as coeffect keys `camera.model` and `lens.model`. Stages that need them **declare** them in `requires`. When absent, those stages **never activate** — Cordis's reactive coeffect (§1.4) gives us graceful degradation for free — and the pipeline falls back to a scale-estimating aligner that solves for magnification numerically.

**The pipeline must not error when a model is missing. It must get slightly worse.** That is the whole point of making them optional, and it is a testable invariant: for any stack, the pipeline must produce a result with the models present, absent, and partially present.

## 4.8 Where we deliberately refuse to be pluggable

Naming the rigid seams is as important as naming the flexible ones. These stay closed:

1. **The buffer / allocator / device layer.** One arena, one `wgpu` device, one staging path. **No plugin allocates.** (This is what makes zero-copy true rather than aspirational.)
2. **The scheduler and tiler.** Plugins *declare* resources; the framework *decides*. Ceding this loses the ability to fit 24 GB into 32 GB of VRAM+RAM.
3. **The pixel data model** — domains, layouts, numeric types. Adding a `Domain` is a core change, reviewed as such.
4. **RAW decode → linearization, and the colour/whitepoint invariants.** Demosaic is a plugin; *what a linear scene-referred value means* is not.
5. **Error, cancellation and progress.** One mechanism, framework-owned. (nushell's out-of-band `Signal`/Interrupt is the model to copy.)
6. **Legal stage orderings.** Order is declarative data, but *constrained* by the framework's domain algebra — you may not put a Bayer-domain stage after demosaic. darktable's `IOP_FLAGS_FENCE` ("No module can be moved pass this one") is the precedent, and lensfun's non-commutative correction chain is the concrete case.
7. **Determinism and cache keys.** The framework computes hashes; plugins declare their params and version. A plugin that could define its own cache key could silently poison the cache.

## 4.9 Caching — LLVM's invalidation over Nix's derivations

Every stage output is a **derivation** keyed on a content hash of: `(stage id, stage version, param blob, upstream output hashes, device class, precision)`.

- **Nix's discipline** (§3.8): *inputs must be explicitly collected, never scanned for.* A stage that reads an undeclared input silently breaks caching, so the API must make undeclared reads impossible — the stage sees only what it was handed.
- **LLVM's invalidation model** (§3.7): a parameter change invalidates that result and everything transitively downstream, while sibling analyses survive. Concretely: **changing the merge weighting must not invalidate the aligned frames.** For a 40-frame macro stack, alignment is the expensive part and the merge is the part the user actually iterates on. Getting this right is worth more to a user than the entire plugin system.
- **Cordis's committed view `ω`** (§1.6) supplies the missing trigger: invalidate when the *identity of the provider* changes, not merely when a key becomes unbound. Swapping focus-measure plugin A for plugin B must invalidate focus pyramids even though `focus.measure` was bound throughout.
- **libvips's invalidate signal** (§3.3) is the runtime analogue for the in-process case.

## 4.10 The v1 minimum — do exactly this and no more

1. **One binary. All stages in-tree.** `Vec<Box<dyn Stage>>` built from a `pipeline.ron`.
2. **The `Stage` trait of §4.5**, with two-pass ROI negotiation and the `resources()` declaration.
3. **No dynamic loading. No wasm. No DI container.** A `HashMap` of typed keys is the "registry".
4. **GPU via `naga_oil` `virtual`/`override`** for focus measures and merge weights. WGSL only. Framework owns dispatch.
5. **Params: one `serde` struct per stage + `schemars` JSON Schema for UI generation + an explicit `version: u32` and a `migrate(old_version, value)` hook.** This is darktable's `legacy_params` and its `DT_MODULE_INTROSPECTION`, and it comes from twenty years of shipping.
6. **Content-hash caching of aligned frames and focus pyramids to disk.** This is worth more to the user than any plugin system, and it is the feature that makes iterating on merge parameters tolerable.

That is a week or two of architecture, not a quarter.

## 4.11 The don't-foreclose list — cheap now, expensive later

1. **Keep `Stage` object-safe and `Send + Sync`; no borrowed lifetimes in the trait.** Take `&RunCtx`, not `&mut World`. (Bevy's `&mut App` is convenient and is exactly what makes Bevy plugins impossible to move out of process.)
2. **Never pass a raw `&[f32]` where a `TileView` descriptor would do.** The descriptor is what survives a process or wasm boundary later; a bare slice is what makes that migration a rewrite.
3. **Route registration through a `Context`-shaped API from day one:** `ctx.provide::<K>(v) -> Disposer`, `ctx.require::<K>()`, `ctx.add_stage(...)` — even when it is a `HashMap` plus `Drop` underneath. The *shape* is the Cordis shape; it costs nothing now and is what makes optional plugins, hot reload, and per-run isolation realms possible later.
4. **Put `(id, semver, params_hash)` in the cache key from day one.** Retrofitting cache keys is a rewrite, and a subtly-wrong cache is worse than no cache.
5. **Keep the GPU kernel interface at *source-level composition*** (`naga_oil` / WESL / Slang), never "here is a compiled pipeline". **Source composition is what removes the ABI problem entirely**, and it is the load-bearing decision in this whole document.
6. **Manifest-first.** Even in-tree stages declare themselves in a `plugin.toml` (kind, requires, provides, params schema, caps). Out-of-tree loading later then becomes a directory scan rather than an architecture change.
7. **Reserve exactly one `cdylib` seam:** a `#[repr(C)]` `PluginEntry` v-table with a **leading version `u32`**, behind a feature flag, unimplemented in v1. Reserving the shape is free; discovering you need it and having no version word is not.
8. **Do not build:** hot reload, a wasm sandbox, IPC, service brokers, isolation realms, runtime interception. All are recoverable later; none are needed for a batch job.

## 4.12 The over-engineering verdict

**The owner said "might be overkill". They are partly right, and the honest answer is a split, not a defence.**

**Adopt the parts of Cordis that are free:**
- the `(requires, provides, effect-with-inverse)` shape — a closure plus `Drop` in Rust;
- declare-don't-error optional dependencies (this *is* the camera/lens-model requirement);
- **confluence as a testable invariant** — the output is a function of the declared config alone;
- the **ordered-vs-commutative key discipline** — registries commute, the pixel chain does not, so pipeline order must be data.

**Defer the parts that cost:** a runtime DI container, proxied context access, hot reload, dynamic loading, sandboxing, interception. Until a second contributor actually asks.

**Calibration.** Koishi took **four years to accumulate 4000 plugins** (§1.7) in a chatbot ecosystem with an enormous casual-developer population. A focus-stacking application plausibly has **fewer than thirty plugins, ever**, and the dominant cost of the product is alignment and merge *quality*, not the plugin boundary. Cordis's machinery is priced for the former situation. We should buy the *shape* and not the *machinery*.

**The strongest argument for the whole architecture is not extensibility at all — it is that §4.5's declared capabilities and §4.9's caching are what let 24 GB of frames be scheduled and re-run cheaply.** Those pay for themselves on day one with zero external contributors. Extensibility is the second-order benefit. If the plugin system is ever justified on extensibility alone, it is over-engineered.

---

# 5. Gaps and uncertainties

**Explicitly UNVERIFIED — could not confirm:**

1. **`wgpu` 30 raw-Vulkan-handle export (`wgpu::Device::as_hal`).** The docs.rs fetch returned only the error-scope section. This blocks the CUDA fast path's zero-copy story (§2.7.5). **Highest-value follow-up.** Bevy's `raw_vulkan_init` feature is suggestive but not proof.
2. **Bevy's render graph.** `https://docs.rs/bevy_render/latest/bevy_render/render_graph/index.html` and `https://docs.rs/bevy/latest/bevy/render/render_graph/index.html` both 404'd. No claims made.
3. **Blender's node system / OSL on GPU.** `docs.blender.org` returned 403. Not investigated further.
4. **OBS shader plugins.** Never fetched. Not investigated.
5. **`rerun`'s extension model.** Never investigated.
6. **Published wasm-vs-native overhead benchmarks for image workloads.** I found none. The §2.4 argument is *structural* (the Canonical ABI explainer's own words) plus **explicitly-labelled derived arithmetic** (528 MB/frame). No benchmark numbers were invented.
7. **`naga_oil` 0.23.0's `compose` module API surface.** `https://docs.rs/naga_oil/latest/naga_oil/compose/index.html` returned an essentially empty page; all `naga_oil` claims come from the GitHub README, which is detailed and current but is not the API reference.
8. **Cordis v4's actual runtime overhead.** The paper states there are no measurements (§5.3 threats to validity). Any performance claim about Cordis in this report would be invention.

**Reporting nuance:** `wasmtime`'s crates.io record shows `max_stable_version` 48.0.0 while `newest_version` is 36.0.14 — the latter being a patch published later on the older 36.x line. Reported accurately above rather than collapsed to one number.

**Sources whose retrieval required a workaround (recorded so they can be re-fetched):** wasmtime's proposal table (fetch the **raw** `docs/stability-wasm-proposals.md`, not the rendered mdBook page, which strips tables); GStreamer's negotiation design (503 twice on `gstreamer.freedesktop.org`; use the GitLab raw markdown); darktable's pixelpipe documentation (404 on dtdocs; read `src/develop/imageop.h` and `src/iop/iop_api.h` instead — they are better anyway); the Nix derivation manual (404 on nix.dev; use raw markdown from the NixOS/nix repo).

---

# Follow-up 1

Four items: (F1) closing the wgpu→CUDA interop gap; (F2) the `naga_oil` `override` objection, which is correct; (F3) the concrete API; (F4) confluence as a real property test.

**Method note for F1/F2:** I stopped reading documentation and read the **actual crate sources**, downloaded from `https://static.crates.io/crates/<name>/<name>-30.0.1.crate` and extracted locally. Versions inspected: **`wgpu` 30.0.1, `wgpu-hal` 30.0.1, `wgpu-types` 30.0.1** (all confirmed `max_stable_version = 30.0.1` via the crates.io API on 2026-08-22; `wgpu-hal` `updated_at` 2026-08-22). Line numbers below refer to those extracted sources.

---

## F1 — wgpu → CUDA zero-copy on Windows: **it works.** Your suspicion was right about the allocator and wrong about the conclusion.

### F1.1 The suspicion, adjudicated

**You were right that the default path cannot export** — and right about the mechanism, though the crate is not the one you named.

- wgpu-hal 30.0.1's Vulkan backend uses **`gpu_allocator`** (Traverse Research), not `gpu-alloc`. `mem_allocator: Mutex<gpu_allocator::vulkan::Allocator>` — `wgpu-hal-30.0.1/src/vulkan/mod.rs:559`. **VERIFIED.**
- `create_buffer` allocates with **`allocation_scheme: gpu_allocator::vulkan::AllocationScheme::GpuAllocatorManaged`** — `wgpu-hal-30.0.1/src/vulkan/device.rs:1035-1044`. That is **hard-coded**; there is no path by which a user-requested buffer gets `AllocationScheme::DedicatedBuffer`. It then binds with `bind_buffer_memory(raw, allocation.memory(), allocation.offset())` (`device.rs:1064-1066`) — i.e. **sub-allocated at a non-zero offset out of a shared block**. **VERIFIED.**
- `gpu_allocator::vulkan::AllocationCreateDesc` carries `name`, `requirements`, `location`, `linear`, `allocation_scheme` and **nothing else** — there is no field by which `VkExportMemoryAllocateInfo` could be threaded into the `vkAllocateMemory` pNext chain. **VERIFIED** by exhaustion of the struct literal at `device.rs:1036-1044`.

**So: a `wgpu::Buffer` created the normal way is not exportable, and never will be by that path.** `cudaImportExternalMemory` requires memory allocated with an export handle type declared *at allocation time*; you cannot retroactively make an allocation exportable.

### F1.2 But there is a first-class escape hatch, and it is public API

Reading further, wgpu-hal 30.0.1 anticipates exactly this:

```rust
// wgpu-hal-30.0.1/src/vulkan/mod.rs:769-783
/// # Safety
/// - We will use this buffer and the buffer's backing memory range as if we have
///   exclusive ownership over it, until the wgpu resource is dropped and the
///   wgpu-hal object is cleaned up
/// - Externally imported buffers can't be mapped by `wgpu`
/// - `offset` and `size` must be valid with the allocation of `memory`
pub unsafe fn from_raw_managed(
    vk_buffer: vk::Buffer,
    memory: vk::DeviceMemory,
    offset: u64,
    size: u64,
) -> Self
```

backed by `enum BufferMemoryBacking { Managed(gpu_allocator::vulkan::Allocation), VulkanMemory { memory, offset, size } }` (`mod.rs:687-694`). On teardown, the `VulkanMemory` arm calls `self.shared.raw.free_memory(memory, None)` (`device.rs:1086-1088`) — **wgpu takes ownership of the `VkDeviceMemory` and frees it**, which is a clean lifetime story. **VERIFIED.**

And the wrapper crate exposes everything needed to use it:

| API | Location | **VERIFIED** |
| --- | --- | --- |
| `wgpu::Device::as_hal::<A>` | `wgpu-30.0.1/src/api/device.rs:668` | ✔ |
| `wgpu::Device::create_buffer_from_hal::<A>(hal_buffer, desc)` | `wgpu-30.0.1/src/api/device.rs:463` | ✔ |
| `wgpu::Buffer::as_hal::<A>` | `wgpu-30.0.1/src/api/buffer.rs:290` | ✔ |
| `wgpu::Adapter::create_device_from_hal` | `wgpu-30.0.1/src/api/adapter.rs:77` | ✔ |
| `wgpu_hal::vulkan::Queue::raw_device() -> &ash::Device` | `wgpu-hal-30.0.1/src/vulkan/mod.rs:1520` | ✔ |

**The extension is enabled for us already.** `VK_KHR_external_memory_win32` is pushed onto the device extension list **unconditionally whenever the physical device supports it** — it is not gated on the user requesting the feature bit:

```rust
// wgpu-hal-30.0.1/src/vulkan/adapter.rs:1339-1342
// Optional `VK_KHR_external_memory_win32`
if self.supports_extension(khr::external_memory_win32::NAME) {
    extensions.push(khr::external_memory_win32::NAME);
}
```

and the capability is surfaced as a real, user-requestable wgpu feature: `Features::VULKAN_EXTERNAL_MEMORY_WIN32 = 1 << 45`, documented *"Allows using the [VK_KHR_external_memory_win32] Vulkan extension"* — `wgpu-types-30.0.1/src/features.rs:1210-1219`, set from `caps.supports_extension(khr::external_memory_win32::NAME)` at `wgpu-hal-30.0.1/src/vulkan/adapter.rs:1053-1056`. **VERIFIED.**

### F1.3 Synchronisation is solved too — and this was the part I expected to fail

`cudaImportExternalSemaphore` needs an exportable semaphore that both sides can signal and wait. wgpu-hal exposes **public** hooks to inject arbitrary semaphores, **including timeline semaphores with values**:

```rust
// wgpu-hal-30.0.1/src/vulkan/mod.rs:1524-1531
pub fn add_signal_semaphore(&self, semaphore: vk::Semaphore, semaphore_value: Option<u64>) {
    let mut guard = self.signal_semaphores.lock();
    if let Some(value) = semaphore_value {
        guard.push_signal(SemaphoreType::Timeline(semaphore, value));
    } else {
        guard.push_signal(SemaphoreType::Binary(semaphore));
    }
}

// wgpu-hal-30.0.1/src/vulkan/mod.rs:1552-1561
pub fn add_wait_semaphore(
    &self,
    semaphore: vk::Semaphore,
    semaphore_value: Option<u64>,
    stage: vk::PipelineStageFlags,
)
```

These feed `SemaphoreList::add_to_submit`, which pushes a `vk::TimelineSemaphoreSubmitInfo` onto the `vk::SubmitInfo` (`mod.rs:1480-1487`, `semaphore_list.rs:81-109`). **VERIFIED.** That pairs directly with CUDA's `cudaExternalSemaphoreHandleTypeTimelineSemaphoreWin32` (value 10, from the CUDA external-resource-interop docs cited in §2.7.5).

### F1.4 The verified recipe

1. Request `Features::VULKAN_EXTERNAL_MEMORY_WIN32` at device creation.
2. `device.as_hal::<wgpu_hal::api::Vulkan>()` → `ash::Device` + `ash::Instance`.
3. Create the `VkBuffer` yourself with `vk::ExternalMemoryBufferCreateInfo{ handle_types: OPAQUE_WIN32 }` in the pNext chain.
4. `vkAllocateMemory` yourself with `vk::ExportMemoryAllocateInfo{ handle_types: OPAQUE_WIN32 }` **and** `vk::MemoryDedicatedAllocateInfo` (NVIDIA generally requires dedicated for external). Bind at **offset 0** — we control the allocation, so no sub-allocation offset.
5. `wgpu_hal::vulkan::Buffer::from_raw_managed(buf, mem, 0, size)`, then `device.create_buffer_from_hal::<Vulkan>(hal_buf, &desc)` → a real `wgpu::Buffer`.
6. Load `ash::khr::external_memory_win32::Device::new(&instance, &device)` yourself (wgpu-hal stores only the **fd** variant — `external_memory_fd: Option<khr::external_memory_fd::Device>` at `mod.rs:330`, with no Win32 sibling — so we load the fn pointers ourselves; the extension is already enabled, which is all that is required). Call `get_memory_win32_handle` → `HANDLE`.
7. `cudaImportExternalMemory` + `cudaExternalMemoryGetMappedBuffer` → a `CUdeviceptr` aliasing the same VRAM.
8. Create an exportable timeline `VkSemaphore` (`vk::ExportSemaphoreCreateInfo`), import it with `cudaImportExternalSemaphore`, and thread it through `add_signal_semaphore` / `add_wait_semaphore`.
9. **Ownership discipline (from the CUDA docs, §2.7.5):** for `OpaqueWin32` ownership is **not** transferred to CUDA, so we must `CloseHandle` ourselves — and only *after* the import. The `VkDeviceMemory` is owned by wgpu (freed in `destroy_buffer`), so the CUDA-side mapping must be destroyed **before** the `wgpu::Buffer` drops.

**Constraint worth flagging:** `from_raw_managed`'s safety contract says *"Externally imported buffers can't be mapped by `wgpu`"*. So a shared buffer cannot also be a `MAP_READ` staging buffer. Fine — shared buffers are `GpuOnly` intermediates by construction.

### F1.5 Ranked fallbacks (now largely moot, but priced)

Since the primary path works, these are contingency only. Ranked as you asked:

- **(a) Drop `wgpu`, go straight to `ash`.** *Rejected.* We would be writing our own swapchain, allocator, descriptor management, and shader pipeline for the sake of one allocation flag we can already override. It also forfeits the DX12/Metal backends, i.e. the entire "portable GPU baseline" requirement. Cost: months. Benefit: none we don't already have.
- **(c) CUDA as a fully separate backend owning its own allocations end to end.** *This is the actual fallback, and it is also the sane v1 posture.* The pipeline picks **one** device backend per run; a stack is processed entirely on wgpu or entirely on CUDA. No sharing, no interop, no handle lifetimes. Costs one extra decode→upload if a run switches backends, which it does not do mid-run. **Choose this for v1 regardless**, and treat F1.4 as the v2 optimisation that lets a *single* run mix a CUDA aligner with a wgpu merger.
- **(b) Accept a device-to-device copy at the CUDA boundary.** *Third.* Priced: `cudaMemcpyDeviceToDevice` on a 5090 runs at roughly HBM/GDDR7 bandwidth — call it ~1.0-1.5 TB/s of achievable copy throughput (read+write halves that in effective terms). *This is derived arithmetic from vendor bandwidth class, NOT a fetched benchmark — treat as an order-of-magnitude estimate only.* At 528 MB/frame and 40 frames = 21 GB, a full round trip is ~2 × 21 GB / ~1.2 TB/s ≈ **35 ms**. That is genuinely cheap versus a multi-second alignment. So option (b) is not the disaster it looks like — **which is the real reason not to panic about this question at all.**

**Recommendation: (c) for v1, F1.4 for v2, (b) as the always-available correctness fallback, (a) never.**

---

## F2 — You are right: `override` is the wrong tool. Here is the mechanism argument.

### F2.1 Three disqualifying properties of `naga_oil`'s `virtual`/`override`

All three come from the semantics in the `naga_oil` README (**VERIFIED**, §2.7.1), not from taste:

1. **It is total replacement, not addition.** *"an override replaces all calls to the original in the entire shader scope (except calls inside the override itself)."* Two focus measures in one shader means the second one **shadows** the first — you do not get both, you get the winner. **This alone kills "run several and combine" and "A/B two in the same build."** It is not a limitation we can work around; it is what the feature *is*.
2. **Resolution is by import-graph position, not by configuration.** Overrides *"form a stack ordered by first occurrence in a depth-first search of the import tree."* So "which focus measure am I using" becomes a property of **import order**. That is precisely the anti-pattern the Cordis paper identifies (§3.3.2, p.25): an **ordered chain** masquerading as a **commutative registry**. And it directly violates the confluence invariant I proposed in §4.9/§4.12 — the result would no longer be a function of the declared configuration alone. **Your instinct that "that would be a bad seam" is exactly right, and it is the same defect Cordis names.**
3. **Plugins could not ship self-contained modules anyway.** Overrides *"can currently only be defined in WGSL"* and *"must be declared in the top-level shader or imported as an `additional_import`"* — a plain `#import` will not work, due to tree-shaking. So every plugin override has to be threaded into the *root* shader by the framework. The mechanism does not even give us the encapsulation that would justify its cost.

**Where `override` is still right:** exactly one place — framework-level *policy* where precisely one implementation is correct and it is fixed for the whole run, e.g. substituting the CFA-sampling function for an unusual sensor layout, or swapping a bounds-check for an unchecked variant in a release build. Keep it there. **Do not use it for algorithm selection.** Revised from §4.6 of the main report, which overstated its role.

### F2.2 The three candidates, evaluated on your four criteria

**Candidate A — distinct entry points / distinct specialized pipelines, selected by name at pipeline-build time; `naga_oil` used only for *code sharing*.**

Each contributed measure is an ordinary WGSL function with a distinct name (`fm_tenengrad`, `fm_laplacian_var`, `fm_dct_energy`), living in a module the framework imports. The framework *generates* the `@compute` entry point that calls the selected one(s) by name.

- *Runtime switching cost:* zero at dispatch — swapping which pipeline is bound is a `set_pipeline`. Build cost is paid once per variant, at plan time.
- *20 measures in a build:* you compile only the variants the config names, not all 20. Critically, wgpu's override processing is **entry-point-scoped** — `process_overrides(&module, &info, Some((naga_stage, stage.entry_point)), stage.constants)` (`wgpu-hal-30.0.1/src/vulkan/device.rs:770-774`, **VERIFIED**) — so one composed naga module can carry all 20 functions while each pipeline emits SPIR-V for only the reachable subgraph.
- *Two measures in one dispatch:* **yes, trivially.** Because they are plain named functions rather than shadowing overrides, the generated entry point can call `fm_a(...)` and `fm_b(...)` and combine the results in one pass, with one read of the pixel data. **This is the decisive advantage** — for a 33 MP × 40-frame stack, fusing two measures into one dispatch versus two saves an entire 21 GB read.
- *Compile-time explosion:* linear in *used* variants, not *installed* variants. Cache emitted SPIR-V by content hash of (module set, entry point, constants) and it is amortised to zero across runs.

**Candidate B — one kernel with a `switch` over a uniform/push-constant selector.**

- *Runtime switching cost:* genuinely free — write a different value into a uniform, no rebuild at all. This is its only real advantage.
- *20 measures in a build:* **this is where it dies.** All 20 bodies are compiled into one kernel, so register allocation is the **max over all 20**, and occupancy for the whole dispatch is set by the worst-behaved contributed measure. One plugin author who writes a register-hungry 9×9 DCT measure silently halves the throughput of every other measure in the build. That is an unacceptable coupling between independent contributors.
- *Two in one dispatch:* awkward — two selectors, two switch sites, and the register pressure of both.
- *Compile time:* every build compiles all 20 even though one runs.
- *Verdict:* correct for a **small, closed, framework-owned** set — boundary handling mode, precision, CFA phase. Wrong for an open, contributed set.

**Candidate C — `wgpu` pipeline-overridable constants.**

- *Expressiveness:* `pub constants: &'a [(&'a str, f64)]` — `wgpu-30.0.1/src/api/common_pipeline.rs:7-17`, documented as *"the values of pipeline-overridable constants in the shader module… The value may represent any of WGSL's concrete scalar types."* **VERIFIED.** **Scalars only, keyed by name, typed `f64`.** You cannot name a function with one. You could pass an integer ID and `switch` on it — but that is Candidate B with extra steps.
- *Actual cost, which is not what most people assume:* wgpu does **not** lower these to Vulkan `VkSpecializationInfo`. There is no `SpecializationInfo` anywhere in the Vulkan backend (grepped `wgpu-hal-30.0.1/src/vulkan/` for `SpecializationInfo|specialization` — **one** hit, and it is `naga::back::pipeline_constants::process_overrides`). Instead, at **each pipeline creation** it runs `process_overrides` to constant-fold the values into the naga IR, then a full `naga::back::spv::write_vec`, then `create_shader_module_impl` to make a **fresh `VkShaderModule`** (`device.rs:770-786`). **VERIFIED.** So an override-constant variant costs a complete backend re-emission — the *same* order of cost as Candidate A, with strictly less expressive power.
- *Verdict:* the right tool for **numeric schedule parameters** — workgroup size, tile dimensions, channel count, halo width — and nothing else.

### F2.3 The resolution, and why it is the Halide split again

**Use Candidate A for algorithm selection. Use Candidate C for schedule parameters. Use Candidate B only for small closed framework-owned sets. Use `override` only for whole-run policy substitution.**

That partition is not arbitrary — it is exactly §2.7.4's Halide split falling out of the mechanisms:

- **the algorithm** (which focus measure) → selected **by name**, monomorphized into its own entry point → Candidate A;
- **the schedule** (tile size, workgroup shape) → framework-owned numeric parameters → Candidate C.

The plugin never chooses its schedule and the framework never chooses its algorithm, and the two mechanisms are the two the toolchain actually implements well.

**Slang is the strictly better version of Candidate A** and remains the v2 target: `extern struct Measure : IFocusMeasure;` resolved by `export struct Measure : IFocusMeasure = Tenengrad;` at **link time** reuses all front-end work instead of re-running the backend per variant (§2.7.3, **VERIFIED** from the Slang link-time-specialization page). It also gets us CUDA and SPIR-V from one source. The migration path from Candidate A to Slang is short precisely *because* selection is already by name rather than by shadowing.

---

## F3 — The API

Compiling-quality definitions. Types elided for brevity are marked `/* … */`; everything structural is spelled out.

### F3.1 Identity, versioning, hashing

```rust
use std::any::TypeId;
use std::collections::BTreeMap;
use std::marker::PhantomData;
use std::sync::Arc;

/// Stable, human-readable stage identity. Part of every cache key.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub struct StageId(pub &'static str);

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
}

/// The framework owns hashing. Stages *feed* it; they never define a cache key.
/// (Rigid seam #7, main report §4.8.)
pub trait ParamHash {
    fn hash_params(&self, h: &mut blake3::Hasher);
}
```

### F3.2 `TileView` — the descriptor, and who owns the allocation

The invariant: **a `TileView` is a borrow, never an owner.** The framework's arena owns every allocation; a stage that wants to keep data past `run` must ask the framework for an output buffer.

```rust
/// Where the pixels currently live. Never owns; always borrows from the arena.
#[derive(Clone, Copy)]
pub enum Storage<'a> {
    /// Host-resident, in the framework's pinned arena.
    Host { bytes: &'a [u8] },

    /// Resident on the portable GPU baseline. The framework owns the buffer.
    Wgpu {
        buffer: &'a wgpu::Buffer,
        offset: u64,
        size: u64,
    },

    /// Resident in CUDA. When `CudaInterop` is active this *aliases the same
    /// VkDeviceMemory* as the `Wgpu` variant (Follow-up 1 §F1.4) -- same bytes,
    /// different handle. When it is not, this is a distinct allocation and the
    /// framework inserted an explicit transfer.
    Cuda { device_ptr: u64, size: u64 },
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Roi {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
}

#[derive(Clone, Copy, Debug)]
pub struct TileGeom {
    /// Region this tile covers in the *frame's* coordinate system.
    pub roi: Roi,
    /// Valid (non-halo) sub-region. Writes outside this are discarded.
    pub valid: Roi,
    pub row_stride_bytes: u32,
    pub plane_stride_bytes: u32,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Precision { U16, F16, F32 }

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum ScalarSemantic { Sharpness, Weight, Depth, Confidence, Mask }

/// The pixel data model. Rigid seam #3: adding a variant is a core change.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Domain {
    Bayer { cfa: CfaLayout, black: [u16; 4], white: [u16; 4] },
    LinearRgb { primaries: Primaries },
    Scalar { semantic: ScalarSemantic },
}

pub struct TileView<'a> {
    pub storage: Storage<'a>,
    pub geom: TileGeom,
    pub domain: Domain,
    pub precision: Precision,
    /// Which frame of the stack this tile belongs to. `None` for merged results.
    pub frame: Option<u32>,
}

pub struct TileViewMut<'a> {
    pub storage: StorageMut<'a>,
    pub geom: TileGeom,
    pub domain: Domain,
    pub precision: Precision,
    pub frame: Option<u32>,
}

pub enum StorageMut<'a> {
    Host { bytes: &'a mut [u8] },
    Wgpu { buffer: &'a wgpu::Buffer, offset: u64, size: u64 },
    Cuda { device_ptr: u64, size: u64 },
}

/// Everything a stage is allowed to touch, in one place. Nix's rule (§3.8):
/// inputs are *handed over*, never scanned for -- a stage physically cannot
/// read an undeclared input, so the cache key cannot silently go stale.
pub struct StageIo<'a> {
    pub inputs: &'a [TileView<'a>],
    pub outputs: &'a mut [TileViewMut<'a>],
    /// Named side-channel products (darktable's raster masks, §3.1).
    pub aux_in: &'a BTreeMap<&'static str, TileView<'a>>,
}
```

### F3.3 Capabilities and negotiation

```rust
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum DeviceClass { Cpu, Wgpu, Cuda }

/// The single most important capability (main report §4.5).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Access {
    /// Tileable. Needs `halo` pixels of context outside `valid`.
    Streaming { halo: u32 },
    /// Needs one whole frame resident.
    WholeFrame,
    /// Needs all N frames resident simultaneously. The scheduler must see this
    /// *before* it commits to a tiling plan.
    WholeStack,
}

#[derive(Clone, Debug)]
pub struct Caps {
    pub domains_in: Vec<Domain>,
    pub domains_out: Vec<Domain>,
    pub devices: Vec<DeviceClass>,
    pub precisions: Vec<Precision>,
    pub access: Access,
    /// darktable's `IOP_FLAGS_FENCE`: no stage may be reordered across this one.
    pub fence: bool,
}

#[derive(Clone, Copy, Debug)]
pub struct Agreed {
    pub domain_in: Domain,
    pub domain_out: Domain,
    pub device: DeviceClass,
    pub precision: Precision,
}

/// darktable's `tiling_callback`: "factor * input_size + overhead".
#[derive(Clone, Copy, Debug)]
pub struct Resources {
    pub factor: f32,
    pub overhead_bytes: u64,
    pub halo: u32,
    pub access: Access,
}
```

### F3.4 `Stage` — object-safe, `Send + Sync`, dual-path with fallback

```rust
pub trait Stage: Send + Sync + 'static {
    fn id(&self) -> StageId;
    fn version(&self) -> Version;

    fn caps(&self) -> Caps;

    /// GStreamer's rule (§3.4): downstream *suggests*, upstream *decides*.
    fn negotiate(&self, downstream: &Caps) -> Result<Agreed, NegotiateError>;

    /// darktable `modify_roi_out`, first pass, traversed first -> last.
    fn roi_out(&self, roi_in: Roi) -> Roi { roi_in }

    /// darktable `modify_roi_in`, second pass, traversed last -> first.
    fn roi_in(&self, roi_out: Roi) -> Roi { roi_out }

    fn resources(&self, roi_in: Roi, roi_out: Roi) -> Resources;

    fn hash_params(&self, h: &mut blake3::Hasher);

    /// REQUIRED, exactly like darktable's `process`. Every stage has a CPU path;
    /// this is what makes the GPU genuinely optional rather than load-bearing.
    fn run_cpu(&self, ctx: &RunCtx<'_>, io: &mut StageIo<'_>) -> Result<(), StageError>;

    /// OPTIONAL, exactly like darktable's `process_cl`. `None` => framework
    /// silently falls back to `run_cpu`, no error, no warning at plan time.
    fn gpu(&self) -> Option<&dyn GpuStage> { None }
}
```

Object safety: no generic methods, no `Self` in return position, no associated types. `&dyn GpuStage` rather than `impl GpuStage` is deliberate. Lifetimes in argument position are fine.

### F3.5 `GpuStage` — kernel bodies, never pipelines

```rust
pub struct ShaderSource {
    /// `#define_import_path`-style module name.
    pub module_path: &'static str,
    pub wgsl: &'static str,
}

pub enum Dispatch {
    /// The overwhelmingly common case: framework generates the entry point,
    /// picks the workgroup shape, and dispatches. Plugin writes no host code.
    PerPixel,
    PerTile,
    /// Escape hatch. Still cannot allocate or submit -- only record into the
    /// framework's encoder.
    Custom,
}

pub trait GpuStage: Send + Sync {
    /// Contributed WGSL. MUST NOT declare `@compute` entry points and MUST NOT
    /// use `override fn` for algorithm selection (Follow-up 1 §F2).
    fn shader(&self) -> ShaderSource;

    /// The function the generated entry point calls, BY NAME. Candidate A.
    /// Selection is a property of configuration, never of import order.
    fn kernel_fn(&self) -> &'static str;

    /// Schedule parameters only -- scalars, folded in at pipeline build time via
    /// `PipelineCompilationOptions::constants`. Never used to select an algorithm.
    fn schedule_constants(&self) -> &[(&'static str, f64)] { &[] }

    fn dispatch(&self) -> Dispatch { Dispatch::PerPixel }

    /// Only called when `dispatch() == Custom`.
    fn encode(&self, _ctx: &GpuRunCtx<'_>, _io: &mut StageIo<'_>) -> Result<(), StageError> {
        Ok(())
    }
}
```

Because `kernel_fn` returns a name, **fusing two focus measures into one dispatch is a framework decision**, made by generating an entry point that calls both — no plugin cooperation required.

### F3.6 `RunCtx`

```rust
pub struct RunCtx<'a> {
    pub agreed: Agreed,
    pub frame_count: u32,
    pub camera: Option<&'a dyn CameraModel>,
    pub lens: Option<&'a dyn LensModel>,
    pub cancel: &'a CancelToken,
    pub progress: &'a dyn Fn(f32),
    scratch: &'a Arena,
}

impl<'a> RunCtx<'a> {
    /// The ONLY way a stage obtains memory. Rigid seam #1.
    pub fn scratch(&self, bytes: usize) -> ScratchHandle<'a> { self.scratch.alloc(bytes) }
}
```

`camera` and `lens` are `Option` **at the point of use as well as at the point of provision** — a stage that got activated because the key was bound still has to cope with an individual query returning `None` (F3.8).

### F3.7 `Context`, `Effect`, and the Cordis inverse discharged by `Drop`

```rust
/// A typed coeffect key. Cordis `K` with its dependent value type `V_k`,
/// expressed as Rust's `trait` + associated type -- the exact mechanism the
/// paper names for Rust in §6.4.
pub trait Key: 'static {
    type Value: Send + Sync + 'static;
    const NAME: &'static str;
}

/// Cordis's witnessed inverse. The `Option` is the paper's `armed` flag
/// (Algorithm 1): disposal happens at most once.
pub struct Disposer(Option<Box<dyn FnOnce() + Send>>);

impl Disposer {
    pub fn new(f: impl FnOnce() + Send + 'static) -> Self {
        Disposer(Some(Box::new(f)))
    }
    pub fn noop() -> Self { Disposer(None) }
}

impl Drop for Disposer {
    fn drop(&mut self) {
        if let Some(f) = self.0.take() {
            f();
        }
    }
}

/// The accumulator `phi`. `Vec` + reverse-order drop *is* twisted composition
/// (Def 1): inverses compose in the opposite order to the forward maps, so LIFO
/// disposal is structural rather than something we have to remember.
#[derive(Default)]
pub struct Effect {
    inverses: Vec<Disposer>,
}

impl Effect {
    pub fn track(&mut self, d: Disposer) { self.inverses.push(d); }
}

impl Drop for Effect {
    fn drop(&mut self) {
        while let Some(d) = self.inverses.pop() {
            drop(d); // LIFO. Thm 16 needs no extra hypothesis in this order.
        }
    }
}

pub struct Context {
    store: BTreeMap<&'static str, Box<dyn std::any::Any + Send + Sync>>,
    provider_of: BTreeMap<&'static str, StageId>,
}

impl Context {
    /// Cordis `set`: provision is ITSELF a revertible effect (§3.2). Registration
    /// and deregistration are one code path, so there is no half-registered state.
    #[must_use = "dropping the Disposer immediately withdraws the provision"]
    pub fn provide<K: Key>(&mut self, by: StageId, value: K::Value) -> Disposer {
        self.store.insert(K::NAME, Box::new(value));
        self.provider_of.insert(K::NAME, by);
        // NOTE: a real implementation shares the maps via Arc<Mutex<..>>; shown
        // inline here so the inverse is visible next to the effect that needs it.
        Disposer::new(move || { /* store.remove(K::NAME); provider_of.remove(K::NAME); */ })
    }

    pub fn require<K: Key>(&self) -> Option<&K::Value> {
        self.store.get(K::NAME)?.downcast_ref::<K::Value>()
    }

    /// Cordis's committed view `omega` (§4.2): record WHICH stage provided a key,
    /// not just that it is bound. Swapping provider A for provider B must
    /// invalidate derived artefacts even though the key stayed bound throughout.
    pub fn provider_of(&self, key: &'static str) -> Option<StageId> {
        self.provider_of.get(key).copied()
    }
}
```

### F3.8 Activation: an unsatisfied optional dependency leaves a stage **inactive, not failed**

```rust
pub enum Activation {
    Active(Effect),
    /// NOT an error. The plan records this and carries on.
    Inactive { unmet: Vec<&'static str> },
}

pub trait Component: Send + Sync + 'static {
    fn id(&self) -> StageId;
    /// Cordis `d`. Checked before `activate` is ever called.
    fn requires(&self) -> &'static [&'static str] { &[] }
    /// Cordis `p`. Nothing outside this set may be provided.
    fn provides(&self) -> &'static [&'static str] { &[] }
    /// Cordis `e`: the witnessed effect. Every provision returns its inverse.
    fn activate(&self, ctx: &mut Context) -> Result<Effect, ActivateError>;
}

pub fn try_activate(c: &dyn Component, ctx: &mut Context) -> Activation {
    let unmet: Vec<_> = c.requires()
        .iter()
        .copied()
        .filter(|k| ctx.provider_of(k).is_none())
        .collect();

    if !unmet.is_empty() {
        // Def 26 `notify` returned neither activating nor deactivating.
        // The camera/lens model is simply absent; degrade, do not fail.
        return Activation::Inactive { unmet };
    }
    match c.activate(ctx) {
        Ok(e) => Activation::Active(e),
        // Cordis FAILED = Inactive(xi) (§4.3): a failure to activate is still
        // just inactivity, and the accumulator has already unwound.
        Err(e) => Activation::Inactive { unmet: vec![e.key] },
    }
}
```

The plan carries `Vec<Inactive>` as **diagnostics**, surfaced to the user as *"lens model unavailable for FE 90mm F2.8 Macro G OSS — falling back to solved scale"*. The run does not fail.

### F3.9 Camera and lens models: **priors, never capability**

Designed to the parallel optics workstream's conclusion. Every accessor is `Option`, and `None` means *"I do not know"* — which **disables** the correction rather than approximating it.

```rust
pub trait CameraModel: Send + Sync {
    fn matches(&self, id: &CameraId) -> bool;

    fn cfa(&self) -> Option<CfaLayout>;
    fn black_white(&self, iso: f32) -> Option<BlackWhite>;
    /// sigma^2 = a*x + b, per ISO. `None` => merger uses an estimated-from-data model.
    fn noise(&self, iso: f32) -> Option<NoiseModel>;
    fn pdaf_map(&self) -> Option<&PdafMap>;
    fn color_matrix(&self, illum: Illuminant) -> Option<ColorMatrix>;
}

#[derive(Clone, Copy, Debug)]
pub struct LensState {
    pub focal_mm: f32,
    pub f_number: f32,
    pub focus: Option<FocusPosition>,
}

pub trait LensModel: Send + Sync {
    fn matches(&self, id: &LensId) -> bool;

    // --- Geometric corrections. `None` DISABLES the correction. ---
    // A model MUST NOT extrapolate a polynomial to an unmeasured (focal,
    // aperture, focus) triple. A wrong coefficient applied confidently is worse
    // than no correction, because the aligner then has to undo it.
    fn distortion(&self, s: LensState) -> Option<DistortionPoly>;
    fn tca(&self, s: LensState) -> Option<TcaPoly>;
    fn vignetting(&self, s: LensState) -> Option<VignettePoly>;

    // --- Priors. These inform a solver; they never replace it. ---

    /// Expected magnification change between two focus positions.
    /// Returns `None` when the lens has no breathing measurement at all.
    fn breathing_prior(&self, from: FocusPosition, to: FocusPosition) -> Option<ScalePrior>;

    fn focus_distance(&self, p: FocusPosition) -> Option<Meters>;
}

/// A prior is a distribution, not a number. `sigma` is MANDATORY: a model that
/// is confident and wrong is the failure mode we are designing against, so
/// there is deliberately no constructor that omits it.
#[derive(Clone, Copy, Debug)]
pub struct ScalePrior {
    pub ratio: f64,
    /// 1-sigma on `ratio`. Used as the regularizer weight in the aligner's
    /// objective. Large sigma => the prior is nearly ignored, which is the
    /// correct behaviour for a lens we only half know.
    pub sigma: f64,
}
```

**How a prior composes with the measured result.** The reference-rig measurement is **−1.012 % total scale drift over 33 frames**, with the scale centre roughly **400 px off image centre**. Two consequences the API must encode:

1. 33 frames is **32 intervals**, so the per-interval ratio is `0.98988^(1/32) ≈ 0.99968`, i.e. about **−0.032 % per frame** — a ~10 px displacement at the corner of a 6000 px-wide frame, which is far too large to ignore and far too small to eyeball. *(Derived arithmetic from the supplied measurement, not a fetched figure.)*
2. **The centre is not the image centre and must be solved per stack** — it moves with sensor shift, tripod flex, and the particular rail run. A lens model must therefore **never supply a centre**; supplying one would be exactly the "confident instrument" failure mode.

```rust
#[derive(Clone, Copy, Debug)]
pub struct ScaleSolution {
    pub ratio: f64,
    /// Solved PER STACK, in pixels, in frame coordinates. Measured ~400 px from
    /// image centre on the reference rig, so `[w/2, h/2]` is not a safe default
    /// and is not offered as one.
    pub centre: [f64; 2],
    pub residual_px: f64,
    /// True when a `ScalePrior` was available and actually moved the solution.
    pub prior_used: bool,
}

pub trait Aligner: Send + Sync {
    /// `prior` is `Option` at the call site as well as at provision: the lens
    /// model may exist and still decline to answer for this focus pair.
    fn solve_scale(
        &self,
        frames: &FrameSet,
        prior: Option<ScalePrior>,
    ) -> Result<ScaleSolution, AlignError>;
}
```

The aligner minimises reprojection residual with the prior as a **regularizer weighted by `1/sigma^2`**, so `sigma -> inf` degrades continuously to the unregularised solve. Degradation is graceful **by construction**, not by a branch.

### F3.10 `pipeline.ron`

```ron
Pipeline(
    schema: 1,
    // Content-addressed cache root. Nix's discipline (§3.8): every input that
    // affects an output is named here; nothing is scanned for.
    cache: (dir: ".fscache", enabled: true),

    device: Auto,          // Auto | Cpu | Wgpu | Cuda
    precision: F32,

    // Commutative registry: order here is NOT significant, and the confluence
    // test in F4 asserts exactly that.
    models: [
        (kind: "camera", id: "sony.ilce7rm5",        source: Builtin),
        (kind: "lens",   id: "sony.fe90mm.f28.macro", source: File("lenses/fe90.ron")),
    ],

    // Ordered chain: order here IS significant and is the ONLY thing that
    // determines execution order. Never emergent from registration or imports.
    stages: [
        (id: "io.raw.rawler",        version: "^0.7", params: (
            paths: Glob("stack/*.ARW"),
            reference_frame: Auto,
        )),
        (id: "pre.linearize",        version: "^1.0", params: (
            use_camera_black: true,      // degrades to per-frame estimate if absent
        )),
        (id: "pre.pdaf_repair",      version: "^1.0", params: ()),
        (id: "pre.denoise.bayer",    version: "^1.2", params: (
            strength: 0.4,
            noise_model: FromCamera,     // falls back to Estimated when None
        )),
        (id: "align.scale_affine",   version: "^2.0", params: (
            breathing_prior: FromLens,   // falls back to Solved when None
            solve_centre: true,          // ALWAYS true; see F3.9
            max_iterations: 60,
        )),
        (id: "focus.measure",        version: "^1.0", params: (
            // Selection BY NAME (Candidate A). Two measures fused into one
            // dispatch by the framework -- not two passes over 21 GB.
            measures: [
                (name: "fm_tenengrad",   weight: 0.6, params: (window: 5)),
                (name: "fm_laplacian_var", weight: 0.4, params: (window: 3)),
            ],
            pyramid_levels: 5,
        )),
        (id: "merge.pyramid",        version: "^1.1", params: (
            levels: 5,
            halo_suppression: 0.7,
        )),
        (id: "post.demosaic.amaze",  version: "^1.0", params: ()),
        (id: "post.lens_correct",    version: "^1.0", params: (
            // lensfun's ordering is framework-fixed (§3.9); these only ENABLE.
            vignetting: FromLens,
            tca:        FromLens,
            distortion: FromLens,
        )),
        (id: "io.write.tiff",        version: "^1.0", params: (
            path: "out/stacked.tif",
            bits: 16,
            compression: Deflate,
        )),
    ],
)
```

`FromLens` resolving to `None` at runtime means **the correction is skipped and a diagnostic is emitted** — never an error, and never an approximation.

---

## F4 — Confluence as a property test that can actually fail

The trap you named is real: a test asserting only *"the output is stable under permutation"* is passed trivially by a pipeline that always returns a constant. So the suite needs **three** properties, and only the conjunction has teeth.

### F4.1 What `proptest` generates

```rust
use proptest::prelude::*;

#[derive(Clone, Debug)]
struct Scenario {
    cfg: PipelineConfig,
    /// Order in which stage crates register themselves with the Context.
    registration_order: Vec<usize>,
    /// Order of `models:` entries -- a COMMUTATIVE registry, per Cordis p.25.
    model_order: Vec<usize>,
    /// Order of keys within each params record (RON map ordering).
    field_order: Vec<usize>,
    /// Order in which the shader composer walks the import tree.
    import_order: Vec<usize>,
}

fn arb_scenario() -> impl Strategy<Value = Scenario> { /* … */ }

/// Two configs guaranteed to differ in a way that MUST change pixels:
/// a different focus measure, a different merge level count, a different
/// alignment prior, or a toggled correction.
fn arb_distinguishable_pair() -> impl Strategy<Value = (PipelineConfig, PipelineConfig)> { /* … */ }
```

Note what is **not** permuted: the `stages:` list. That is the ordered chain, and permuting it is *supposed* to change the result. Permuting it and asserting invariance would be the tautology in reverse.

### F4.2 Property 1 — confluence (Cordis Thm 73)

```rust
proptest! {
    #[test]
    fn plan_and_output_are_a_function_of_config_alone(s in arb_scenario()) {
        let canonical = build_plan(&s.cfg, Perm::identity());
        let permuted  = build_plan(&s.cfg, Perm::from(&s));

        // (a) the resolved plan is identical, including which stages went Inactive
        prop_assert_eq!(canonical.canonical_hash(), permuted.canonical_hash());
        prop_assert_eq!(canonical.inactive_stages(), permuted.inactive_stages());

        // (b) so is every cache key derived from it
        prop_assert_eq!(canonical.cache_keys(), permuted.cache_keys());

        // (c) and so are the actual pixels, bit for bit, on a small fixture
        let a = run(&canonical, &FIXTURE_8_FRAMES).digest();
        let b = run(&permuted,  &FIXTURE_8_FRAMES).digest();
        prop_assert_eq!(a, b);
    }
}
```

### F4.3 Property 2 — sensitivity (this is the anti-tautology clause)

```rust
proptest! {
    #[test]
    fn distinguishable_configs_produce_distinguishable_output(
        (c1, c2) in arb_distinguishable_pair()
    ) {
        let d1 = run(&build_plan(&c1, Perm::identity()), &FIXTURE_8_FRAMES).digest();
        let d2 = run(&build_plan(&c2, Perm::identity()), &FIXTURE_8_FRAMES).digest();
        prop_assert_ne!(d1, d2, "config change had no observable effect: {:?} vs {:?}", c1, c2);
    }
}
```

**This is the property that a constant-returning instrument fails.** Property 1 alone is satisfied by `fn run(_) -> [0u8; N]`.

### F4.4 Property 3 — no residue across runs (Cordis Cor 62, terminal recovery)

```rust
proptest! {
    #[test]
    fn a_run_leaves_nothing_behind(s in arb_scenario()) {
        let mut ctx = Context::default();
        let d1 = { let _e = activate_all(&s.cfg, &mut ctx); run_in(&ctx, &FIXTURE_8_FRAMES).digest() };
        // every Effect has now dropped; the Context must be observationally clean
        prop_assert!(ctx.is_empty(), "leaked provisions: {:?}", ctx.bound_keys());

        let d2 = { let _e = activate_all(&s.cfg, &mut ctx); run_in(&ctx, &FIXTURE_8_FRAMES).digest() };
        prop_assert_eq!(d1, d2, "second run in the same process differed -- residual state");
    }
}
```

### F4.5 Property 4 — the calibrated fixture (instrument validation, distinct from confluence)

Confluence tests say nothing about *correctness*. So, separately, a synthetic stack built to the measured rig characteristics:

```rust
#[test]
fn solver_recovers_known_scale_drift() {
    // 33 synthetic frames, ground-truth total scale -1.012 %, centre offset
    // (+412, -180) px from image centre, plus realistic sensor noise.
    let stack = synth_stack(Frames(33), TotalScale(0.98988), Centre([412.0, -180.0]));

    let sol = aligner().solve_scale(&stack, None).unwrap();

    assert!((sol.ratio - 0.98988).abs() < 2e-4, "ratio {} off", sol.ratio);
    assert!((sol.centre[0] - 412.0).abs() < 8.0, "centre x {} off", sol.centre[0]);
    assert!((sol.centre[1] + 180.0).abs() < 8.0, "centre y {} off", sol.centre[1]);
    assert!(sol.residual_px < 0.3);
}
```

### F4.6 The faults I would deliberately inject, and which property catches each

A test suite nobody has watched go red is not evidence. Four injections, each targeting one property:

| # | Injected fault | Caught by | Why this fault |
| --- | --- | --- | --- |
| 1 | Select the focus measure via `naga_oil` `override` (DFS import order) instead of by name | **P1** — permuting `import_order` changes the pixels | This is not hypothetical: it is precisely the design in §4.6 of the main report that F2 rejects. The test is what proves F2's argument empirically. |
| 2 | `FocusMeasure::measure` returns a plausible constant `0.5`; or `breathing_prior` returns `Some(ScalePrior{ ratio: 1.0, sigma: 1e-9 })` — confident and wrong | **P2** (and **P4**) — P1 still passes | Your named failure mode. A confident-constant instrument is *perfectly confluent*. Only sensitivity and the calibrated fixture see it. |
| 3 | `std::mem::forget` an `Effect`, or swap `Vec`+pop for `Vec`+`drain(..)` (FIFO instead of LIFO disposal) | **P3** — the second run differs | Breaks Cordis's twisted composition. FIFO disposal is the subtlest of the four and would survive code review. |
| 4 | Build the stage registry with `HashMap` and iterate it directly | **P1**, but *only* if the harness re-seeds `RandomState` per case | **Worth stating explicitly:** `HashMap` iteration order is stable *within a process*, so a naive in-process proptest would **miss this**. The harness must either use an explicitly-seeded hasher it can vary, or run cases in subprocesses. This is a place where a plausible-looking test is silently blind. |

Fault 2 is the one you asked about, and the honest answer is that **the confluence property cannot catch it, by construction** — confluence is a statement about *determinism*, and a constant is maximally deterministic. It is caught only by P2's sensitivity assertion and P4's calibrated fixture. That is the argument for shipping all four properties rather than the elegant one.

### F4.7 Cost

`FIXTURE_8_FRAMES` should be 8 frames at ~512×512, not 40 at 33 MP — the properties are about *plan resolution and ordering*, which are resolution-independent. Full-resolution runs belong in a nightly job, not in `cargo test`.

---

## Follow-up 1 — gaps and uncertainties

- **VERIFIED by reading source:** everything in F1 and F2 attributed to `wgpu` / `wgpu-hal` / `wgpu-types` 30.0.1, with file and line numbers, from crate tarballs downloaded from `static.crates.io`.
- **NOT tested at runtime.** I read the source; I did not compile and run the F1.4 recipe against an actual RTX 5090. The API surface is confirmed to exist and to be public; the *runtime* behaviour (in particular whether the NVIDIA Windows driver requires `MemoryDedicatedAllocateInfo` for `OPAQUE_WIN32` buffer exports, and whether `vkGetMemoryWin32HandleKHR` succeeds for a buffer rather than an image) is **UNVERIFIED**. This should be a ~200-line spike before any architecture depends on it.
- **The ~1.0-1.5 TB/s figure in F1.5(b) is a bandwidth-class estimate, not a fetched benchmark.** Explicitly derived, not measured. The ~35 ms round-trip figure inherits that uncertainty.
- **`gpu_allocator`'s own crate version and API were not independently fetched** — my claims about `AllocationCreateDesc`'s fields are inferred from the exhaustive struct literal in `wgpu-hal-30.0.1/src/vulkan/device.rs:1036-1044`, which is strong but indirect evidence. Confidence: high; primary source: not read.
- **Slang's CUDA back-end quality for our specific kernels is UNVERIFIED.** The target list is documented (§2.7.3); the generated-code quality versus hand-written CUDA is not something I found data on.
- **The −1.012 % / 400 px figures are taken from the orchestrator's brief**, attributed to a parallel optics workstream. I did not independently verify them; the per-interval derivation (−0.032 %/frame) is my arithmetic on those inputs.
