# MQTT Command Interface (Runtime Control)

These documents describe an MQTT-driven runtime control interface for managing BLE sessions and issuing commands without
recompiling firmware.

## Design Goals

- Single-shot commands (no polling)
- Explicit timeouts for connect/pair operations
- Deterministic state feedback via status topics
- Safe failure behavior (`disconnect_on_fail`)

## Recommended Topic Layout

### Commands (HA → ESP32)

- `gira/<node_id>/cmd` (payload is a single-line command string)

### Status / Events (ESP32 → HA)

- `gira/<node_id>/status` (connection and state machine)
- `gira/<node_id>/event` (parsed device events)
- `gira/<node_id>/debug` (optional, high-volume)

## Payload Format (Command String)

Commands use a stable `key=value` syntax:

- `connect addr=E8:2B:E7:A3:06:74 addr_type=random timeout_ms=15000 disconnect_on_fail=1`
- `pair timeout_ms=20000 probe=none disconnect_on_fail=1`
- `subscribe notify=1`
- `shutter move=up`
- `shutter set_pos=45`
- `disconnect reason=user`

## Return/Status Format

Status messages should be JSON for machine parsing.

Minimum recommended fields:

```json
{
  "ts": "2026-01-20T12:00:00+01:00",
  "state": "READY",
  "connected": true,
  "encrypted": true,
  "bonded": true,
  "peer": "E8:2B:E7:A3:06:74"
}
```

See the other files in this folder for command-specific details.
