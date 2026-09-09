# Independent native integration results

VERIFIED from native-112-1 receipts: six full renders of the same eight-frame 112MSDCF prefix complete successfully. Every 7032x4688 RGB16 TIFF matches both the saved native anchor and the fresh CPU arms, whole-file SHA256 ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6, decoded uint16 SHA256 d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a.
I independently rehashed the remosaic GPU, rounded GPU and rounded-placebo whole TIFFs; all match. Other complete-file and decoded identities were checked in the saved individual/aggregate receipts; no reviewer RAW decode, pixel-metric run or render occurred.

Both actual paths are live: GPU remosaic and rounded-direct arms each log eight completed RGB calls and eight completed green-only probe calls. CPU arms log zero GPU calls. Both optional features are in the bound executable; the rounded comparison does not merely repeat remosaic under an ignored flag.
The rounded statistics observer has off/on/fixed-placebo arms with identical complete TIFF hashes. The on log contains real measured values; the placebo contains one initialization and sixteen fixed call messages, while successful route markers remain live. This establishes observer nonperturbation on the rendered output, not equality of every internal beta bit.
The cached eight-frame map, same commands, same executable and fixed defect-off/green-probe/parallel-writeback settings are retained. No alignment solve or calibration change is tested here.

Observed complete-process costs (statistics off; not an ABBA benchmark):
| Path | CPU wall s | GPU wall s | CPU owned CPU s | GPU owned CPU s |
|---|---:|---:|---:|---:|
| Remosaic | 5.094 | 8.157 | 26.265625 | 16.156250 |
| Rounded direct | 4.640 | 7.953 | 25.750000 | 15.203125 |
The GPU observer-on/placebo runs took 7.890/7.922 wall seconds. This order is CPU/GPU then CPU/GPU on a different mode, followed by GPU observers; it does not provide alternating reverse comparisons within one setting. No stable speed ratio or observer overhead estimate is justified.
Nevertheless, this implementation demonstrates no elapsed-time improvement in the observed comparisons. Reduced owned CPU time is a different outcome from lower latency. Host busy fractions include these jobs and differ with CPU usage; they do not independently measure background contention.

DERIVED by adding already logged intervals in the observer-on run: sixteen library calls total 4.892888 s, comprising 3.517382 s CPU coordinate preparation, 0.205173 s packing and 1.169286 s submit/wait/readback. Coordinates are 71.89% of those library calls and 44.58% of the 7.890 s complete process. Printed intervals are rounded and these are wall intervals, not CPU samples or GPU timestamp measurements.
Re-choosing the view from whole-process to consumer phases reaches the same diagnosis: rounded gather/probe intervals are 3.327921/2.475048 s with GPU versus 1.370903/1.110481 s with CPU. Other visible decode/add/write phases do not explain that increase. The evidence supports targeting coordinate preparation and batching next, without predicting their eventual benefit.
All six jobs have exit0, terminal accounting, no cleanup errors and no intervention: 114.093750 aggregate child CPU seconds, 41.656 summed process-wall seconds. Peak Job commit is 3,554,394,112 bytes; these totals exclude compilation and earlier controls.

Bound revision b6f5f6be8df15dc57dc499cc2683470550c35750; executable SHA256 809d0c3d935fc5e01df90b9379776a4d03a48210561964dbe029338fbf208c40 and build invocation SHA256 96e4217c128f5d3d9bb71ba8a70e723bacd3e7223d8d80e39255908af484774f were rechecked. The build logs a fresh Compiling strehl-cli line. Native results SHA256 3fa2a5ca44b9ab566ebbbf5a1403996056bc4ca8c1c3e04123aa056f600a0a8c.
Decision: native output-equivalence checkpoint passes for this eight-frame population and both paths. Keep the GPU experimental/default-off and defer the proposed full109 timing comparison while the measured initial bottleneck is addressed. No speed promotion, photographic-quality advantage, general RAW equivalence or SOTA conclusion is established.
