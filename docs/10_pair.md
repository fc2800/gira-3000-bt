# Command: pair

Initiates BLE security (SMP) pairing using **Just Works**, with bonding enabled.

## Command

```
pair timeout_ms=20000 probe=none disconnect_on_fail=1
```

## Parameters

- `timeout_ms` (required): SMP/encryption completion timeout.
- `probe` (optional): determines whether the controller performs pre-checks before starting SMP.
  - `none` (default): start SMP immediately
  - `read_security_state`: read current security flags first (implementation-dependent)
- `disconnect_on_fail` (optional, default `1`):
  - `1`: disconnect if SMP fails or times out
  - `0`: remain connected (only recommended for debugging)

## Expected State Transitions

- CONNECTED → SECURITY_START → PAIRING → ENCRYPTED

After encryption completes, the controller should publish a status update and allow `subscribe` and application commands.

## Failure Indicators

- `ENC_CHANGE timeout`
- repeated SMP retries (example: `security retry rc=2`)

## Recovery Recommendations

- retry pairing with bounded attempts
- if repeated failures occur: clear local bond and re-pair
