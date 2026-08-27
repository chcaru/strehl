"""Build a negative-control harness from BUILD-TRIAGE's, WITHOUT editing theirs.

Pre-registered fail mode for the subprocess route: "a subprocess that dies for
any reason looks like a kill".  Add three controls their suite does not have:
  nc_crash     -- lands, then dies of an UNRELATED exception   -> must FAIL
  nc_noland    -- anchor does not land                          -> must FAIL
  nc_wronggate -- killed by the WRONG gate (the original bug)   -> must FAIL
"""
import io
SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE\mutatetest.py"
DST = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-TRIAGE\harness_nc.py"
src = io.open(SRC, encoding="utf-8").read()

ANCHOR = "MUTATIONS = {\n    \"wording\": (\"noise_phrase -> _legacy_noise_phrase (the form that shipped)\",\n                _mutate_wording, \"noise wording disagrees\"),"
if src.count(ANCHOR) != 1:
    raise SystemExit("ANCHOR DID NOT LAND (%d matches) -- their file changed" % src.count(ANCHOR))

EXTRA = (
 "def _mutate_nc_crash(triage) -> bool:\n"
 "    # Lands, then kills the process with an exception that is NOT a gate.\n"
 "    def boom():\n"
 "        raise RuntimeError(\"unrelated boom -- not a gate firing\")\n"
 "    triage.main = boom\n"
 "    return True\n\n\n"
 "def _mutate_nc_noland(triage) -> bool:\n"
 "    # Simulates an anchor that stopped matching.\n"
 "    return False\n\n\n"
 "def _mutate_nc_wronggate(triage) -> bool:\n"
 "    # The ORIGINAL bug: contaminate wording AND drop a definition.\n"
 "    # Declared token is UNDEFINED, but the wording gate fires first.\n"
 "    triage.commission_wording = lambda: None\n"
 "    triage.noise_phrase = triage._legacy_noise_phrase\n"
 "    triage.FIELD_DEFS.pop(\"noise_flat\", None)\n"
 "    return True\n\n\n"
 + ANCHOR + "\n"
 "    \"nc_crash\": (\"NEGATIVE CONTROL: dies of an unrelated exception\",\n"
 "                 _mutate_nc_crash, \"UNDEFINED\"),\n"
 "    \"nc_noland\": (\"NEGATIVE CONTROL: anchor does not land\",\n"
 "                  _mutate_nc_noland, \"UNDEFINED\"),\n"
 "    \"nc_wronggate\": (\"NEGATIVE CONTROL: killed by the WRONG gate\",\n"
 "                     _mutate_nc_wronggate, \"UNDEFINED\"),")

out = src.replace(ANCHOR, EXTRA, 1)
if out == src:
    raise SystemExit("PATCH DID NOT APPLY")
io.open(DST, "w", encoding="utf-8").write(out)
print("wrote harness_nc.py")
print("their file untouched: %s" % (io.open(SRC, encoding="utf-8").read() == src))
