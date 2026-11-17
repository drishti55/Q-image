# Superseded: E7-mnv3-logreg partial run (runner integration bug)

These experiment directories were produced on 2026-11-13 by the first Phase 3 MobileNetV3 run.
`FrozenMobileNetV3Source.describe()` included `load_info`, which is filled only after the weights are
loaded; the provider description is part of the configuration hash, so the configuration key changed
between the first and later candidates and selection raised `KeyError`. No test evaluation was performed
in this run. Fix: `load_info` moved out of the hashed description into per-experiment diagnostics.
The directories are kept unchanged for traceability and are excluded from all v2 analyses.
