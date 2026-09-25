# Native tile follow-up

The first diagnostic saved 600-700 pixel crops. AGENTS rule 48 requires native visual judgments from unresampled tiles no larger than 400 pixels. The same retained TIFF regions have now been split into overlapping 384x384 tiles, with no resampling and the original ICC; `native-tiles.json` records 24 exact native coordinates. This changes no source or rendered pixel.

Command run: `python -I -B -X faulthandler experiments/quality-september25/marigold/inspect-outputs.py` using the stated Python312 interpreter.

Five tiles were actually inspected: stack4 fan offsets (0,0) and (216,216), left rim offsets (0,0) and (266,216), central throat offset (0,116). The soft/transparent-looking hair outlines and broad haze described in the diagnostic are visible in these smaller native displays too. The source interpretation remains bounded: real hair outlines occur in RAW witnesses, so removing faint lines without protecting those witnesses is unsafe. The withdrawn gross-placement hypothesis stays withdrawn. No gain or source-detail superiority is claimed.

The complete four output previews and full-resolution delivered masters remain the whole-image context. This addendum is separate from the frozen diagnosis report; it does not silently replace its original inspection record.
