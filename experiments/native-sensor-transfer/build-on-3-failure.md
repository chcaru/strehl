# Third native diagnostic build: Windows path spelling refusal

MEASURED: exact source/release87365753a499887b06cbe56d7049c9af20a4b642.
External exit1,4.5 seconds, no timeout. Owned terminal Job CPU6.609375 seconds,
zero active processes after failure cleanup. No native tests or RAW decode.

The unchanged scratch scanner rejected target/native-sensor-transfer-on-3/
debug/deps/rustcdxSn8A because Windows resolve returned the same drive path
with the verbatim prefix. The saved child-00.json retains both exact strings.
The refusal arose before the corrected adapter could compile; it supplies no
new compiler or pixel result. Full600CPU/300wall allocation remains charged.

Root authorizes an experiment-local copy of the held scratch shim, changing
only ordinary/verbatim absolute-drive normalization for equality. Keep all
reparse, containment, missing-file and retained-artifact checks. Use a compact
independently chosen pure-path control set, not another filesystem campaign.
The original shared scanner remains unchanged. Fresh build-on4 uses the same
finite per-build bounds; build-off1 remains unvisited. Earlier failures and
source archives stay preserved. No physics, operator or tolerance change.
