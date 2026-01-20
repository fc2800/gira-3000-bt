# Troubleshooting (MQTT Runtime Control)

## Symptom: ENC_CHANGE timeout

Likely causes:
- SMP not completed
- bond keys mismatch

Actions:
- retry `pair` once with a higher `timeout_ms`
- if repeated: clear bond and re-pair

## Symptom: security retry rc=2

Likely causes:
- peer-side bond conflicts
- sequence mismatch in SMP flow

Actions:
- disconnect and retry
- clear bond on both sides where possible

## Symptom: no notifications

Likely causes:
- `subscribe notify=1` not executed or CCCD write failed
- wrong characteristic resolved

Actions:
- ensure CCCD subscription succeeds
- verify characteristic UUID mapping

## Symptom: shutter stops but no STOP event

Actions:
- implement stop inference: position unchanged for N ms
- publish an explicit `{ "stopped": true }` event at that moment
