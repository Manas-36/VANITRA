# Real glove recordings

`collect_data.py` saves takes here as `<LABEL>/<user>_<YYYYMMDD_HHMMSS>.csv` — commit them, they are the most valuable thing in the repo.

Columns: `t_ms, flex1..flex5 (0 straight..1 bent), hall1..hall4 (0/1), ax, ay, az (g), gx, gy, gz (deg/s)` at 50 Hz, already calibrated.
Checklist per session: glove calibrated for this person · ≥ 5 takes per sign · extra REST takes · note anything unusual in the commit message.
