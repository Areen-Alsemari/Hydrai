"""Compressed gaseous hydrogen (CGH2) storage twin.

A NEW system next to the LH2 twin: nothing in here changes LH2 behaviour. The LH2 twin is the backup system; select this one with
`system="cgh2"` (see hydrai_twin/systems.py). Label for the dashboard everywhere: reference configuration, not a verified Saudi system.

Every number carries a source tag (registry.py): V1 read at the primary document / datasheet, V2 reputable secondary, V3 existence only,
U not found, CALC our calculation, JUDGE decision without a source, REG-UNREAD relayed in the instruction from the decision register
(the register file itself was not available when this was built). Anything U, JUDGE or REG-UNREAD is a flagged placeholder.
"""
