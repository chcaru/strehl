# Second native diagnostic build: compiler refusal

MEASURED: source/release139d1034749eebf481e6e2274cfbf7726abff79c.
The second build reached strehl-cli with incremental compilation disabled.
Cargo exited101 after one reported syntax error in the experiment adapter:
source/native-adapter.rs:278, json! does not accept the unparenthesized literal
array followed by .map in the model_planes field. The field needs expression
parentheses; no sensor/merge arithmetic change is required.

The external wrapper returned1 after55.063 seconds without timeout. Complete
owned Job CPU is100.875 seconds and terminal active processes zero; the process
helper refused its compile-only successful-exit cleanup branch because Cargo
had failed, then performed owned failure cleanup. The full600CPU/300wall
allocation remains additional to attempt1. No test, control or RAW decode ran.

Root authorizes the ordinary syntax correction and one fresh fixed build-on3,
with the same600CPU/300wall/3GiB Job/128MiB output/4GiB scratch allocation.
Build-off1 remains unvisited. Both failures and their source archives remain.
No scientific criterion, population, tolerance or interpretation changes.
