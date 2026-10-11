# ADR-0007: Initial audience and privacy gate

**Status:** Accepted · **Date:** 2026-10-11

## Context

The game is educational and may be used by minors or in schools. The legal jurisdiction, age range, deployment model, and applicable privacy rules were not specified. Collecting learner data or enabling external AI before those are known creates avoidable risk.

## Decision

- Initial product positioning is secondary/tertiary education (older teens and adult learners); do not market as an early-childhood product.
- Do not enable production student accounts, classroom analytics, or external AI processing until launch jurisdiction, minimum age/consent model, data residency, retention/deletion, and school/guardian obligations are reviewed and approved.
- Minimize data by default; synthetic data only in development; analytics and raw learner-source transfer to AI are disabled by default.
- The audience decision does not assert legal compliance or resolve exact age limits. Those remain a release gate.

## Consequences

The product and curriculum may target secondary/tertiary learners now, while deployment and data collection remain gated. Privacy requirements must be revisited before pilot. This decision constrains launch readiness, not local synthetic-data development.

## References

[Product requirements and SRS](../01-product-requirements.md), [UX and analytics](../05-ux-dashboards-multiplayer.md), [risk register](../06-quality-delivery-roadmap.md#4-risk-register).
