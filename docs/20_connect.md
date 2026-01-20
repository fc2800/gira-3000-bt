# Command: connect

Connects to a specific BLE peer address and establishes a GATT session.

## Command

```
connect addr=E8:2B:E7:A3:06:74 addr_type=random timeout_ms=15000 disconnect_on_fail=1
```

## Parameters

- `addr` (required): BLE MAC (AA:BB:CC:DD:EE:FF)
- `addr_type` (optional):
  - `public`
  - `random` (commonly used by many BLE devices)
- `timeout_ms` (required): connect timeout.
- `disconnect_on_fail` (optional, default `1`): disconnect if connect fails.

## Expected State Transitions

- IDLE → SCANNING → CONNECTING → CONNECTED

After CONNECTED:
- perform GATT discovery/resolve characteristics
- optionally proceed with `pair`

## Failure Indicators

- connect timeout
- GATT discovery failure (missing characteristics)

## Notes

If the peer uses resolvable private addresses (RPA), address management requires IRK-based resolution; otherwise, use the
observed address plus `addr_type`.
