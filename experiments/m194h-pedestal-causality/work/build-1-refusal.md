# Build1: successful compiler, refused process-tree completion

MEASURED by one source-frozen capture-stage.py build invocation at release commit5e19f02a73162300d51db460a230aaa4251a742a. No component, render or checker ran.

Cargo's first compile returned0, printed Compiling strehl-core and fresh compiler-artifact/build-finished success; pipe EOF was observed. Post-exit drain began10.375seconds with active_processes1. The record retained13,351 observations and still observed1 until the child wall limit at224.453seconds. The owned Job was then terminated successfully; terminal accounting had active0 and cleanup_errors was empty. No background executable identity was retained. Do not call it telemetry, harmless or naturally complete.

Actual outer exit1, timeout_terminated=false, whole225.21899999999732seconds. Parent CPU sample81.015625 plus completed Job21.21875; tail allowance2. Retain full original build grant300CPU/240wall as spent allocation, not measured CPU. Original result stays REFUSED. The speculative scratch-scan explanation was not established: repeated scans consumed overhead, but retained active Job membership directly explains the pending drain.

No CLI compile/test listing/artifact copy was reached. The old compiler log and scratch remain preserved. A separate source-frozen build2 is authorized by root's continuation decision, with a build-only intentional owned-descendant cleanup policy after observed direct Cargo exit0 and actual pipe EOF. That cannot convert this attempt into success.
