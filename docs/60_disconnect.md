# Command: disconnect

Terminates the current BLE connection.

## Command

```
disconnect reason=user
```

## Parameters

- `reason` (optional): free text for logs/status

## Expected State Transitions

- READY/ENCRYPTED/CONNECTED → DISCONNECTING → IDLE

## Notes

A disconnect should flush pending writes and stop notification processing cleanly.
