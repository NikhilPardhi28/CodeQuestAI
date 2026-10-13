using System.Threading;
using System.Threading.Tasks;

namespace CodeQuest.Networking
{
    /// <summary>Provides short-lived OIDC access tokens from a configured identity adapter.</summary>
    public interface IAccessTokenProvider
    {
        Task<string> GetAccessTokenAsync(CancellationToken cancellationToken);
    }

    public interface IInteractiveAuthenticationProvider : IAccessTokenProvider
    {
        bool IsSignedIn { get; }
        Task<bool> SignInAsync(CancellationToken cancellationToken);
    }

    /// <summary>Fail-closed fallback when no supported platform identity adapter is composed.</summary>
    public sealed class UnauthenticatedTokenProvider : IAccessTokenProvider
    {
        public Task<string> GetAccessTokenAsync(CancellationToken cancellationToken)
        {
            return Task.FromResult<string>(null);
        }
    }
}
