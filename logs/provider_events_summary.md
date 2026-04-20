# Provider Events Summary

- source: `C:\Users\zhang\Desktop\DN\logs\provider_events.jsonl`
- total events: `110`
- rate limited events: `0`
- acquired events: `57`
- avg queue wait: `52196.21` ms
- p95 queue wait: `143175` ms

## Groups

### image / yunwu / scene_image

- events: `24`
- statuses: `{"acquired": 13, "response": 11}`
- priorities: `{"unknown": 24}`
- status codes: `{"200": 11}`
- queue wait(ms): `{"avg": 13175.5, "p50": 0, "p95": 49620, "max": 49620}`
- latency(ms): `{"avg": 40199.73, "p50": 35685, "p95": 61838, "max": 61838}`

### llm / yunwu / chat_completion

- events: `86`
- statuses: `{"acquired": 44, "success": 42}`
- priorities: `{"unknown": 86}`
- status codes: `{}`
- queue wait(ms): `{"avg": 65300.02, "p50": 58859, "p95": 165014, "max": 193398}`
- latency(ms): `{"avg": 42695.24, "p50": 43243, "p95": 76701, "max": 142256}`
