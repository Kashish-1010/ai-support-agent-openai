# HIST-007: Growth upgrade retained Starter concurrency

Source type: history
Product: Acme Sync API v2

Historical customer: Atlas Labs. Resolved before 2026-09-24. Acme Sync API v2, us-east-1. Growth entitlement 20 but enforced concurrency 5. Plan propagation failed. Errors were CONCURRENCY_LIMIT_EXCEEDED when 12 workers ran. An operator approved restoring 5 to 20; fresh requests succeeded afterward. This is a precedent, not evidence of another account’s current state.
