using System;
using CodeQuest.Networking;
using NUnit.Framework;

namespace CodeQuest.Tests.EditMode
{
    public sealed class OidcPkceTests
    {
        [Test]
        public void PkceChallengeMatchesRfc7636S256Vector()
        {
            const string verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
            Assert.AreEqual("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM", WindowsKeycloakTokenProvider.CreateCodeChallenge(verifier));
        }

        [Test]
        public void AuthorizationRequestUsesExactLoopbackRedirectAndS256()
        {
            var request = new Uri(WindowsKeycloakTokenProvider.BuildAuthorizationUri("test-state", "test-challenge"));
            var query = request.Query;
            StringAssert.Contains("response_type=code", query);
            StringAssert.Contains("client_id=codequest-unity", query);
            StringAssert.Contains(Uri.EscapeDataString(WindowsKeycloakTokenProvider.RedirectUri), query);
            StringAssert.Contains("code_challenge_method=S256", query);
            StringAssert.Contains("state=test-state", query);
            StringAssert.Contains("code_challenge=test-challenge", query);
        }

        [Test]
        public void CallbackRequiresExpectedPathStateAndSingleCode()
        {
            Assert.IsTrue(WindowsKeycloakTokenProvider.TryValidateCallback(
                WindowsKeycloakTokenProvider.CallbackPath + "?code=auth-code&state=expected",
                "expected", out var code, out _));
            Assert.AreEqual("auth-code", code);
            Assert.IsFalse(WindowsKeycloakTokenProvider.TryValidateCallback(
                WindowsKeycloakTokenProvider.CallbackPath + "?code=auth-code&state=attacker",
                "expected", out _, out _));
            Assert.IsFalse(WindowsKeycloakTokenProvider.TryValidateCallback(
                "/other/?code=auth-code&state=expected", "expected", out _, out _));
            Assert.IsFalse(WindowsKeycloakTokenProvider.TryValidateCallback(
                WindowsKeycloakTokenProvider.CallbackPath + "?code=one&code=two&state=expected",
                "expected", out _, out _));
        }

        [Test]
        public void CallbackErrorsAndMissingCodesFailClosed()
        {
            Assert.IsFalse(WindowsKeycloakTokenProvider.TryValidateCallback(
                WindowsKeycloakTokenProvider.CallbackPath + "?error=access_denied&state=expected",
                "expected", out _, out _));
            Assert.IsFalse(WindowsKeycloakTokenProvider.TryValidateCallback(
                WindowsKeycloakTokenProvider.CallbackPath + "?state=expected", "expected", out _, out _));
        }

        [TestCase(0)]
        [TestCase(59)]
        [TestCase(86401)]
        public void RejectsInvalidTokenLifetimes(int expiresIn)
        {
            Assert.IsFalse(WindowsKeycloakTokenProvider.IsTokenLifetimeAcceptable(expiresIn));
        }

        [Test]
        public void AcceptsBoundedTokenLifetime()
        {
            Assert.IsTrue(WindowsKeycloakTokenProvider.IsTokenLifetimeAcceptable(300));
        }

        [Test]
        public void TokenResponsesRequireBearerAccessAndRefreshTokens()
        {
            Assert.IsTrue(WindowsKeycloakTokenProvider.IsTokenResponseAcceptable("access", "Bearer", "refresh", 300));
            Assert.IsFalse(WindowsKeycloakTokenProvider.IsTokenResponseAcceptable("", "Bearer", "refresh", 300));
            Assert.IsFalse(WindowsKeycloakTokenProvider.IsTokenResponseAcceptable("access", "MAC", "refresh", 300));
            Assert.IsFalse(WindowsKeycloakTokenProvider.IsTokenResponseAcceptable("access", "Bearer", "", 300));
        }
    }
}
