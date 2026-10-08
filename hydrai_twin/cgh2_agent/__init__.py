"""HYDRAI agent for the CGH2 twin: a tool-using orchestrator, not one learned model.

The agent investigates suspicious behaviour by calling specialist tools (inventory/leak, thermal state, pressure behaviour, sensor integrity, data
integrity, a physics-twin verifier, a forecaster, alarm context, procedures). Each tool studies ONE aspect of the storage system and returns
structured evidence. The orchestrator is a deterministic state machine (policy mode): MONITOR -> SUSPECT -> INVESTIGATE -> DECIDE -> AWAIT_APPROVAL ->
FOLLOW_UP -> CLOSE, and stores a reasoning trace (ordered tool calls, outputs, times) with every decision.

Tools see only what a real dashboard shows (tags, OPC quality, compressor/valve states, the existing alarm state, the clock) plus per-unit and per-class
parameters; the verifier tool may use the twin. No fault labels, onset times, injected-fault flags or paired-twin data are ever inputs.
Reference configuration, not a verified Saudi system.
"""
