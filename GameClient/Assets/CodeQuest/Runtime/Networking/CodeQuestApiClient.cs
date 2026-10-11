using System;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

namespace CodeQuest.Networking
{
    public sealed class CodeQuestApiClient
    {
        private readonly string _baseUrl;
        private readonly int _timeoutSeconds;
        private readonly IAccessTokenProvider _tokenProvider;

        public CodeQuestApiClient(ApiClientSettings settings, IAccessTokenProvider tokenProvider)
        {
            if (settings == null) throw new ArgumentNullException(nameof(settings));
            _baseUrl = settings.BaseUrl;
            _timeoutSeconds = settings.TimeoutSeconds;
            _tokenProvider = tokenProvider ?? throw new ArgumentNullException(nameof(tokenProvider));
        }

        public Task<ApiResult<HealthDto>> GetHealthAsync(CancellationToken token) => GetAsync<HealthDto>("/healthz", false, token);
        public Task<ApiResult<ReadinessDto>> GetReadinessAsync(CancellationToken token) => GetAsync<ReadinessDto>("/readyz", false, token);
        public Task<ApiResult<PageDto<RegionDto>>> GetRegionsAsync(CancellationToken token) => GetAsync<PageDto<RegionDto>>("/api/v1/curriculum/regions", false, token);
        public Task<ApiResult<PageDto<ObjectiveDto>>> GetObjectivesAsync(CancellationToken token) => GetAsync<PageDto<ObjectiveDto>>("/api/v1/curriculum/objectives", false, token);
        public Task<ApiResult<PageDto<QuestDto>>> GetQuestsAsync(CancellationToken token) => GetAsync<PageDto<QuestDto>>("/api/v1/quests", false, token);
        public Task<ApiResult<PageDto<ChallengeDto>>> GetChallengesAsync(CancellationToken token) => GetAsync<PageDto<ChallengeDto>>("/api/v1/challenges", false, token);
        public Task<ApiResult<PlayerProfileDto>> GetMyProfileAsync(CancellationToken token) => GetAsync<PlayerProfileDto>("/api/v1/me", true, token);

        private async Task<ApiResult<T>> GetAsync<T>(string path, bool authenticated, CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(_baseUrl) || !Uri.TryCreate(_baseUrl, UriKind.Absolute, out var baseUri) ||
                (baseUri.Scheme != Uri.UriSchemeHttp && baseUri.Scheme != Uri.UriSchemeHttps))
                return Failure<T>("api_configuration_invalid", "The API base URL is not configured.", 0);

            string accessToken = null;
            if (authenticated)
            {
                try
                {
                    if (_tokenProvider == null || !_tokenProvider.TryGetAccessToken(out accessToken) || string.IsNullOrWhiteSpace(accessToken))
                        return Failure<T>("authentication_required", "Sign in is required to view this profile.", 401);
                }
                catch (Exception)
                {
                    return Failure<T>("authentication_unavailable", "Sign-in is temporarily unavailable.", 503);
                }
            }

            using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(_timeoutSeconds));
                using (var request = UnityWebRequest.Get(new Uri(baseUri, path).ToString()))
                {
                    request.timeout = _timeoutSeconds;
                    request.SetRequestHeader("Accept", "application/json");
                    if (authenticated) request.SetRequestHeader("Authorization", "Bearer " + accessToken);
                    var operation = request.SendWebRequest();
                    try
                    {
                        while (!operation.isDone)
                        {
                            timeout.Token.ThrowIfCancellationRequested();
                            await Task.Yield();
                        }
                    }
                    catch (OperationCanceledException)
                    {
                        request.Abort();
                        return Failure<T>(cancellationToken.IsCancellationRequested ? "request_cancelled" : "request_timeout",
                            cancellationToken.IsCancellationRequested ? "The request was cancelled." : "The backend did not respond in time.", 0);
                    }

                    if (request.result != UnityWebRequest.Result.Success)
                        return ParseFailure<T>(request.downloadHandler == null ? null : request.downloadHandler.text, request.responseCode);

                    try
                    {
                        var value = JsonUtility.FromJson<T>(request.downloadHandler.text);
                        return value == null
                            ? Failure<T>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode)
                            : ApiResult<T>.Success(value, request.responseCode);
                    }
                    catch (ArgumentException)
                    {
                        return Failure<T>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode);
                    }
                }
            }
        }

        private static ApiResult<T> ParseFailure<T>(string body, long statusCode)
        {
            if (!string.IsNullOrEmpty(body))
            {
                try
                {
                    var error = JsonUtility.FromJson<ApiErrorDto>(body);
                    if (error != null && !string.IsNullOrWhiteSpace(error.code) && !string.IsNullOrWhiteSpace(error.message))
                        return ApiResult<T>.Failure(error, statusCode);
                }
                catch (ArgumentException) { }
            }
            var retryable = statusCode == 0 || statusCode >= 500;
            return Failure<T>(retryable ? "service_unavailable" : "http_error",
                retryable ? "The backend is unavailable. Check the connection and try again." : "The request could not be completed.", statusCode);
        }

        private static ApiResult<T> Failure<T>(string code, string message, long statusCode) =>
            ApiResult<T>.Failure(new ApiErrorDto { code = code, message = message, retryable = statusCode == 0 || statusCode >= 500 }, statusCode);
    }
}
