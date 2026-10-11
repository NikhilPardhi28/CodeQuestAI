namespace CodeQuest.Networking
{
    /// <summary>Provides short-lived OIDC access tokens from a configured identity adapter.</summary>
    public interface IAccessTokenProvider
    {
        bool TryGetAccessToken(out string accessToken);
    }

    /// <summary>Honest default until an OIDC provider is selected and configured.</summary>
    public sealed class UnauthenticatedTokenProvider : IAccessTokenProvider
    {
        public bool TryGetAccessToken(out string accessToken)
        {
            accessToken = null;
            return false;
        }
    }
}
