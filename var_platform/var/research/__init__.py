"""Research utilities for the Verified Agent Runtime (VAR).

The core VAR runtime is intentionally small and readable. This package adds optional
features for running reproducible experiments:

- Run manifests: config snapshots, version stamps, environment info.
- Tool I/O recording: capture tool inputs/outputs with configurable redaction.
- State snapshots: time-travel debugging and crash/resume experiments.
- Replay: re-run the agent with mocked tools from a recorded run.
- Fault injection: deterministic tool failures for robustness benchmarking.

These utilities are designed to be swappable so student theses can own individual slices.
"""
