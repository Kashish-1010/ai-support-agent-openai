# HIST-011: 429 after upgrade to Growth

Source type: history
Product: Acme Sync API v2

Historical customer: Beacon Analytics. Resolved before 2026-09-24. Similar title to a concurrency incident, but errors were REQUEST_RATE_EXCEEDED. Account enforcement correctly matched Growth at 20; requests burst above 600/min. Pacing and backoff fixed the issue. Increasing concurrency was not appropriate.
