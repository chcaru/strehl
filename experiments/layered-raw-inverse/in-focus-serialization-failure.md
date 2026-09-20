# First in-focus commission did not complete

MEASURED execution failure, not a quality result. Root ran:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/layered-raw-inverse/run-in-focus-consumer.py --out experiments/layered-raw-inverse/in-focus-1
```

The commission process exited1 after2.234s while serializing its result:
`TypeError: Object of type float32 is not JSON serializable`. The arithmetic
tolerance helper returned a NumPy scalar. No delivered outputs or candidate
scores were produced. Retain the incomplete result.json as a failed artifact,
not a valid receipt. The process log and bound source hashes identify this
revision. Correct only scalar serialization before a fresh output directory;
do not change the controls, thresholds, optical operator or candidate inputs.
