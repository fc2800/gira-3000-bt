# Commands: shutter

Shutter control commands are designed as single-shot writes followed by passive observation of notifications.

## Move Up / Down

```
shutter move=up
shutter move=down
```

### Expected Behavior

- One write is sufficient.
- The device emits position feedback while moving.
- STOP is inferred when position stops changing.

## Stop (optional)

```
shutter stop=1
```

## Set Absolute Position (0–100)

```
shutter set_pos=45
```

## Preconditions

- Connection established (CONNECTED)
- If required by device: encryption active (ENCRYPTED)
- Notifications subscribed (READY)

## Suggested Events (ESP32 → HA)

Example event messages on `gira/<node_id>/event`:

```json
{ "type": "shutter", "peer": "E8:2B:E7:A3:06:74", "position": 12, "moving": true }
{ "type": "shutter", "peer": "E8:2B:E7:A3:06:74", "position": 45, "moving": false, "stopped": true }
```

## Notes

- If the device provides a “movement state” flag, use it.
- Otherwise, infer STOP using a “position unchanged for N ms” rule.
