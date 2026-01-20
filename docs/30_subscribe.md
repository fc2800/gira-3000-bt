# Command: subscribe

Subscribes to notifications (writes CCCD) for the device feedback characteristic.

## Command

```
subscribe notify=1
```

## Parameters

- `notify`:
  - `1` enable notifications
  - `0` disable notifications

## Expected State Transitions

- ENCRYPTED → READY (after CCCD write success)

## Failure Indicators

- CCCD write fails
- no notifications arrive after subscription

## Notes

For device types that only broadcast sensor data via advertisements (no GATT), this command has no effect and should be
rejected with a clear status message.
