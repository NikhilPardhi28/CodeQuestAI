# ADR-0009: Pin installed Unity editor version

**Status:** Accepted · **Date:** 2026-10-11

## Context

The prior baseline required Unity 6 but did not record the installed patch. Inspection found `C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe`. No Unity project or package manifest exists to inspect.

## Decision

Use Unity Editor **6000.3.19f1** for initial project creation and validation. Record the same version in `GameClient/ProjectSettings/ProjectVersion.txt` when the Unity project is scaffolded. Do not auto-upgrade. Select and lock packages through this editor's Package Manager only after project scaffolding; no package versions are pinned in this baseline.

## Consequences

The actual installed patch is reproducible on this workstation. A teammate must install this exact editor version. Package compatibility still needs verification; package dependencies and lockfile are not yet present.

## References

[Unity client architecture](../03-systems-and-client-architecture.md#4-replaceable-interfaces), [toolchain setup](../../CONTRIBUTING.md#toolchain).
