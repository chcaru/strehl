import pathlib,sys,time
mode=sys.argv[1]
summary=b"\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n"
if mode=="zero": sys.stdout.buffer.write(summary)
elif mode=="nonzero": sys.stdout.buffer.write(summary); sys.exit(7)
elif mode=="zero-tests": print("test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s")
elif mode=="duplicate": sys.stdout.buffer.write(summary+summary)
elif mode=="limit": sys.stdout.buffer.write(b"x"*((16<<20)-len(summary))+summary)
elif mode=="overflow": sys.stdout.buffer.write(b"x"*((16<<20)+1)); sys.stdout.flush(); time.sleep(.2)
elif mode=="timeout": print("healthy private timeout fixture",flush=True); time.sleep(5)
elif mode=="change": pathlib.Path(sys.argv[2]).write_bytes(b"changed!"); sys.stdout.buffer.write(summary)
else: raise ValueError(mode)
