# Commands: thermostat

Thermostat interaction is state-driven. Devices report updates autonomously via notifications and/or advertisements
(depending on model).

## Set Target Temperature

```
thermostat set_target_c=21.5
```

## Preconditions

- Connection established and characteristics resolved
- If required: ENCRYPTED
- If the device uses notifications: READY (subscribed)

## Suggested Events

```json
{ "type": "thermostat", "peer": "E8:2B:E7:A3:06:74", "current_c": 20.8, "target_c": 21.5 }
```

## Notes

If a device reports current/target temperatures without a maintained GATT connection, treat updates as advertisements and
do not force a persistent connection.
