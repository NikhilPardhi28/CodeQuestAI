# ADR-0010: OIDC identity boundary with provider deferred

**Status:** Accepted · **Date:** 2026-10-11

## Context

Account authentication is required, but audience, jurisdiction, and deployment host remain unresolved. Choosing a hosted identity vendor now could impose privacy, age, cost, and lock-in consequences.

## Decision

Use an OpenID Connect-compatible identity boundary. BackendAPI validates issuer, audience, signature, expiry, and scopes; the application stores a stable provider subject identifier and application roles, not provider passwords. Provider selection is deferred until the privacy gate and hosting model are approved. Local development uses synthetic identities or a clearly isolated local OIDC development provider; no development bypass may be enabled in production.

## Consequences

Core authorization remains provider-neutral. Provider-specific account recovery, consent, provisioning, and token lifecycle must be implemented and tested after selection. Do not write auth endpoints or persist account data before the identity contract is defined.

**Implementation note (2026-10-11):** the initial API accepts externally issued RS256 OIDC bearer tokens when issuer, audience, and JWKS settings are configured; it does not issue tokens or provide an authentication bypass. The first profile schema maps one configured issuer's `sub` to a profile. Provider selection, account lifecycle, multi-issuer linking, and deployment consent requirements remain open; see the [API route and auth notes](../api/README.md) and [data model notes](../04-services-data-security.md#3-er-model).

## References

[SRS](../01-product-requirements.md), [identity and save data](../04-services-data-security.md#7-identity-authorization-and-save-data).
