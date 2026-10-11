# ADR-0008: Initial supported platform

**Status:** Accepted · **Date:** 2026-10-11

## Context

The project must remain practical to develop on Windows with 16 GB RAM. No platform matrix or minimum hardware was previously set.

## Decision

The first development and validation target is Windows 10/11 x64 desktop. Design input and service boundaries to permit later platform expansion, but do not promise macOS, Linux desktop, mobile, or console support until separately tested and accepted. Final minimum hardware and Windows servicing baseline are release decisions.

## Consequences

One initial platform reduces build/test burden and aligns with the available host. Windows Docker Desktop uses Linux containers for the proposed execution worker; production host/runtime hardening requires a separate review.

## References

[SRS constraints](../01-product-requirements.md#product-constraints), [client architecture](../03-systems-and-client-architecture.md), [delivery plan](../06-quality-delivery-roadmap.md).
