# Local Keycloak 26.8.0 integration

This guide describes local FastAPI validation and the Windows desktop Unity sign-in flow. Unity uses Authorization Code + PKCE S256, a system browser, a fixed loopback listener, in-memory access tokens, and Windows Credential Manager for the refresh token. This is a local development integration, not a production identity deployment.

## Backend settings

Copy `.env.example` to `.env`, then uncomment these three values:

```dotenv
CODEQUEST_AUTH_ISSUER=http://localhost:8080/realms/codequest-dev
CODEQUEST_AUTH_AUDIENCE=codequest-api
CODEQUEST_AUTH_JWKS_URL=http://localhost:8080/realms/codequest-dev/protocol/openid-connect/certs
```

These are the existing `CODEQUEST_AUTH_ISSUER`, `CODEQUEST_AUTH_AUDIENCE`, and `CODEQUEST_AUTH_JWKS_URL` settings; they are not new variables. `CODEQUEST_ENV=local` permits HTTP only for loopback issuer/JWKS hosts. Use HTTPS outside local/test. Never add a client secret or token to `.env.example` or Unity.

Keycloak discovery metadata is at `http://localhost:8080/realms/codequest-dev/.well-known/openid-configuration`. FastAPI does not fetch discovery metadata; it uses the configured JWKS URL directly. The issuer must exactly match the token `iss` value.

## Keycloak client and API audience

For client `codequest-unity`, configure:

- Client authentication **Off** (public client); do not create or embed a client secret.
- Standard flow **On**; Direct access grants and Implicit flow **Off**.
- In **Advanced settings**, set **Proof Key for Code Exchange Code Challenge Method** to **S256**.
- In **Login settings**, set Valid Redirect URIs to exactly `http://127.0.0.1:49173/oidc/callback/`. The Windows implementation binds only that loopback address, port, and callback path. Do not use a wildcard.
- Leave Web Origins empty. This native desktop client does not use browser CORS for UnityWebRequest calls.
- In **Client scopes**, open `codequest-unity-dedicated`, select **Add mapper → By configuration → Audience**, and set Name `codequest-api-audience`, Included Custom Audience `codequest-api`, Add to access token **On**, Add to ID token **Off**, and Add to UserInfo **Off**. This adds only the API audience to access tokens for this client. `azp` or the Unity client ID alone does not satisfy the backend audience check.
- Use RS256 for realm access-token signing. The backend accepts RS256 only and selects the verification key by JWT `kid` from JWKS.

The backend validates signature, exact issuer, audience, `exp`, `iat`, and non-empty `sub`. `sub` is the player identity key; email, preferred username, and `azp` do not determine account ownership.

## Windows Unity desktop authentication

The supported target is Windows Unity Editor and Windows standalone desktop. The UI offers **Sign in with Keycloak** on that platform. It launches the system browser and uses a one-time random `state` and PKCE verifier with S256. The callback accepts only the expected path and Host header on loopback; the code is exchanged with the public client and exact redirect URI. Callback errors, duplicate query fields, wrong state, malformed callbacks, and token failures fail closed. The callback response is fixed content and never redirects to a caller-provided URL.

The access token stays in memory and is injected as `Authorization: Bearer ...` into existing protected API calls. The client refreshes before expiry and stores only the refresh token with the current Windows user's Windows Credential Manager. If the secure store cannot be read or written, authentication fails closed. Tokens, authorization codes, and PKCE verifiers are not logged. Other Unity platforms, including WebGL and macOS/Linux desktop, continue to use the unauthenticated provider until implemented separately. No token is stored in PlayerPrefs.

## Local setup and verification

1. Start Keycloak 26.8.0 and sign into the Admin Console for realm `codequest-dev`.
2. Apply the client configuration and dedicated-scope audience mapper above. Do not create a client secret.
3. Confirm the discovery document reports issuer `http://localhost:8080/realms/codequest-dev`, the JWKS URL `http://localhost:8080/realms/codequest-dev/protocol/openid-connect/certs`, and RS256 signing.
4. Copy `.env.example` to `.env`, uncomment the three local OIDC settings, and run the backend commands in [BackendAPI local setup](../BackendAPI/README.md#local-setup).
5. Open `GameClient` with Unity 6000.3.19f1 on Windows, run Bootstrap, and select **Sign in with Keycloak**.
6. Verify the real access token's `iss`, `aud`, `kid`, `exp`, `iat`, and `sub` without copying it into logs or repository files. Confirm the protected `/api/v1/me` request succeeds, then verify refresh after expiry.

No real credentials or tokens belong in repository files, command history, or logs. See [API authentication notes](api/README.md#known-limitations) and [the identity ADR](adr/0010-identity-provider-boundary.md).
