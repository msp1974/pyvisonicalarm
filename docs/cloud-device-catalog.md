# Cloud device type catalog

PowerManage does not publish a complete public API value list. Treat this as an
observed catalog, not an exhaustive schema. The integration's downloadable
diagnostics include only device type, subtype, whether the pair is mapped, and
the last observed count. Users can share that section when reporting an
unrecognized device; it contains no device IDs, enrollment IDs, names, or
locations.

Add a catalog row only after confirming the exact pair in a sanitized API
response or Home Assistant diagnostics export. Record the source and update the
device mapping plus a mapping test in the same change. Use the observed string
exactly; do not infer values from a marketing name or device class.

| Device type | Subtype | Mapping | Evidence |
| --- | --- | --- | --- |
| `ZONE` | `S_OUT_CURTAIN` | `MotionDevice` | User-supplied issue #291 log |
| `ZONE` | `S_SMOKE_AND_HEAT` | `SmokeDevice` | User-supplied issue #291 log |
| `WIRELESS_COMMANDER` | `PROXIMITY_KEYPAD` | `KeypadDevice` | User-supplied issue #291 log |
| `REPEATER` | `BASIC_REPEATER` | `RepeaterDevice` | User-supplied issue #291 log |
| `WL_SIREN` | `OUTDOOR` | Unmapped | User-supplied issue #291 log |
| `PROXY_TAG` | `GENERIC_PROXY_TAG` | `TagDevice` | User-supplied issue #291 log |
