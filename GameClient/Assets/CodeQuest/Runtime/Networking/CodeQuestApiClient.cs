using System;
using System.Threading;
using System.Threading.Tasks;
using System.Text;
using CodeQuest.Gameplay.Quests;
using UnityEngine;
using UnityEngine.Networking;

namespace CodeQuest.Networking
{
    public sealed class CodeQuestApiClient : IPlayerPersistence
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
        public Task<ApiResult<PageDto<ObjectiveDto>>> GetObjectivesAsync(CancellationToken token) => GetObjectivesAsync(null, token);
        public Task<ApiResult<PageDto<ObjectiveDto>>> GetObjectivesAsync(string regionSlug, CancellationToken token) =>
            GetAsync<PageDto<ObjectiveDto>>("/api/v1/curriculum/objectives" +
                (string.IsNullOrWhiteSpace(regionSlug) ? string.Empty : "?region_slug=" + Uri.EscapeDataString(regionSlug)), false, token);
        public Task<ApiResult<PageDto<QuestDto>>> GetQuestsAsync(CancellationToken token) => GetAsync<PageDto<QuestDto>>("/api/v1/quests", false, token);
        public Task<ApiResult<PageDto<ChallengeDto>>> GetChallengesAsync(CancellationToken token) => GetAsync<PageDto<ChallengeDto>>("/api/v1/challenges", false, token);
        public Task<ApiResult<ChallengeDto>> GetChallengeAsync(string slug, int version, CancellationToken token) =>
            GetAsync<ChallengeDto>("/api/v1/challenges/" + Uri.EscapeDataString(slug) + "/versions/" + version, false, token);
        public Task<ApiResult<ChallengeHintDto>> GetChallengeHintAsync(string slug, int version, int level, CancellationToken token) =>
            GetAsync<ChallengeHintDto>("/api/v1/challenges/" + Uri.EscapeDataString(slug) + "/hints?version=" + version + "&level=" + level, true, token);
        public Task<ApiResult<ChallengeSubmissionDto>> SubmitChallengeAsync(string slug, ChallengeSubmissionRequestDto request, CancellationToken token) =>
            PostAsync<ChallengeSubmissionRequestDto, ChallengeSubmissionDto>("/api/v1/challenges/" + Uri.EscapeDataString(slug) + "/submissions", request, token);
        public Task<ApiResult<ChallengeSubmissionDto>> GetMySubmissionAsync(string submissionId, CancellationToken token) =>
            GetAsync<ChallengeSubmissionDto>("/api/v1/me/submissions/" + Uri.EscapeDataString(submissionId), true, token);
        public Task<ApiResult<PlayerProfileDto>> GetMyProfileAsync(CancellationToken token) => GetAsync<PlayerProfileDto>("/api/v1/me", true, token);
        public Task<ApiResult<PlayerProfileDto>> SaveMyProfileAsync(PlayerProfileUpsertDto profile, CancellationToken token) => PutAsync<PlayerProfileUpsertDto, PlayerProfileDto>("/api/v1/me", profile, token);
        public Task<ApiResult<ProgressionDto>> GetMyProgressionAsync(CancellationToken token) => GetAsync<ProgressionDto>("/api/v2/me/progression", true, token);
        public Task<ApiResult<PageDto<QuestProgressDto>>> GetMyQuestProgressAsync(CancellationToken token) => GetAsync<PageDto<QuestProgressDto>>("/api/v2/me/quests", true, token);
        public bool CanWriteQuestProgress => true;
        public bool IsCloudBacked => true;
        public string StatusLabel => "Quest progress: server authoritative; unconfirmed events show pending or failed";

        public async Task<QuestProgressLoadResult> LoadAsync(CancellationToken cancellationToken)
        {
            var result = await GetMyQuestProgressAsync(cancellationToken);
            if (!result.IsSuccess)
                return QuestProgressLoadResult.Failure(result.Error == null ? "Quest progress could not be loaded." : result.Error.message);
            var items = new System.Collections.Generic.List<QuestEventServerResult>();
            if (result.Value != null && result.Value.items != null)
                foreach (var item in result.Value.items) items.Add(ToServerResult(item));
            return QuestProgressLoadResult.Success(items);
        }

        public async Task<QuestEventSubmissionResult> SubmitAsync(string questSlug, QuestEventRequest request, CancellationToken cancellationToken)
        {
            var result = await PostAsync<QuestEventRequest, QuestEventServerResult>(
                "/api/v2/me/quests/" + Uri.EscapeDataString(questSlug) + "/events", request, cancellationToken);
            if (result.IsSuccess) return QuestEventSubmissionResult.Success(result.Value);
            var currentState = result.Error == null || result.Error.currentState == null ? null : ToServerResult(result.Error.currentState);
            return QuestEventSubmissionResult.Failure(
                result.Error == null ? "request_failed" : result.Error.code,
                result.Error == null ? "Quest event submission failed." : result.Error.message,
                result.Error != null && result.Error.retryable,
                currentState);
        }

        private static QuestEventServerResult ToServerResult(QuestProgressDto value)
        {
            var progress = new System.Collections.Generic.List<QuestObjectiveServerProgress>();
            foreach (var item in value.objectiveProgress ?? System.Array.Empty<QuestObjectiveProgressDto>())
                progress.Add(new QuestObjectiveServerProgress { objectiveId = item.objectiveId, completedCount = item.completedCount, requiredCount = item.requiredCount, completed = item.completed });
            return new QuestEventServerResult { questSlug = value.questSlug, questVersion = value.questVersion, status = value.status, revision = value.revision, objectiveProgress = progress.ToArray() };
        }


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
                    if (_tokenProvider == null || string.IsNullOrWhiteSpace(accessToken = await _tokenProvider.GetAccessTokenAsync(cancellationToken)))
                        return Failure<T>("authentication_required", "Sign in is required to use this service.", 401);
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
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

        private async Task<ApiResult<TResponse>> PutAsync<TRequest, TResponse>(string path, TRequest payload, CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(_baseUrl) || !Uri.TryCreate(_baseUrl, UriKind.Absolute, out var baseUri) ||
                (baseUri.Scheme != Uri.UriSchemeHttp && baseUri.Scheme != Uri.UriSchemeHttps))
                return Failure<TResponse>("api_configuration_invalid", "The API base URL is not configured.", 0);
            if (payload == null) return Failure<TResponse>("request_invalid", "Profile data is required.", 0);
            string accessToken;
            try
            {
                if (_tokenProvider == null || string.IsNullOrWhiteSpace(accessToken = await _tokenProvider.GetAccessTokenAsync(cancellationToken)))
                    return Failure<TResponse>("authentication_required", "Sign in is required to use this service.", 401);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception)
            {
                return Failure<TResponse>("authentication_unavailable", "Sign-in is temporarily unavailable.", 503);
            }

            using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(_timeoutSeconds));
                using (var request = new UnityWebRequest(new Uri(baseUri, path).ToString(), UnityWebRequest.kHttpVerbPUT))
                {
                    request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(JsonUtility.ToJson(payload)));
                    request.downloadHandler = new DownloadHandlerBuffer();
                    request.timeout = _timeoutSeconds;
                    request.SetRequestHeader("Accept", "application/json");
                    request.SetRequestHeader("Content-Type", "application/json");
                    request.SetRequestHeader("Authorization", "Bearer " + accessToken);
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
                        return Failure<TResponse>(cancellationToken.IsCancellationRequested ? "request_cancelled" : "request_timeout",
                            cancellationToken.IsCancellationRequested ? "The request was cancelled." : "The backend did not respond in time.", 0);
                    }
                    if (request.result != UnityWebRequest.Result.Success)
                        return ParseFailure<TResponse>(request.downloadHandler == null ? null : request.downloadHandler.text, request.responseCode);
                    try
                    {
                        var value = JsonUtility.FromJson<TResponse>(request.downloadHandler.text);
                        return value == null ? Failure<TResponse>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode) : ApiResult<TResponse>.Success(value, request.responseCode);
                    }
                    catch (ArgumentException)
                    {
                        return Failure<TResponse>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode);
                    }
                }
            }
        }

        private async Task<ApiResult<TResponse>> PostAsync<TRequest, TResponse>(string path, TRequest payload, CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(_baseUrl) || !Uri.TryCreate(_baseUrl, UriKind.Absolute, out var baseUri) ||
                (baseUri.Scheme != Uri.UriSchemeHttp && baseUri.Scheme != Uri.UriSchemeHttps))
                return Failure<TResponse>("api_configuration_invalid", "The API base URL is not configured.", 0);
            if (payload == null) return Failure<TResponse>("request_invalid", "Request data is required.", 0);
            string accessToken;
            try
            {
                if (_tokenProvider == null || string.IsNullOrWhiteSpace(accessToken = await _tokenProvider.GetAccessTokenAsync(cancellationToken)))
                    return Failure<TResponse>("authentication_required", "Sign in is required to use this service.", 401);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
            catch (Exception)
            {
                return Failure<TResponse>("authentication_unavailable", "Sign-in is temporarily unavailable.", 503);
            }

            using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                timeout.CancelAfter(TimeSpan.FromSeconds(_timeoutSeconds));
                using (var request = new UnityWebRequest(new Uri(baseUri, path).ToString(), UnityWebRequest.kHttpVerbPOST))
                {
                    request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(JsonUtility.ToJson(payload)));
                    request.downloadHandler = new DownloadHandlerBuffer();
                    request.timeout = _timeoutSeconds;
                    request.SetRequestHeader("Accept", "application/json");
                    request.SetRequestHeader("Content-Type", "application/json");
                    request.SetRequestHeader("Authorization", "Bearer " + accessToken);
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
                        return Failure<TResponse>(cancellationToken.IsCancellationRequested ? "request_cancelled" : "request_timeout",
                            cancellationToken.IsCancellationRequested ? "The request was cancelled." : "The backend did not respond in time.", 0);
                    }
                    if (request.result != UnityWebRequest.Result.Success)
                        return ParseFailure<TResponse>(request.downloadHandler == null ? null : request.downloadHandler.text, request.responseCode);
                    try
                    {
                        var value = JsonUtility.FromJson<TResponse>(request.downloadHandler.text);
                        return value == null ? Failure<TResponse>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode) : ApiResult<TResponse>.Success(value, request.responseCode);
                    }
                    catch (ArgumentException)
                    {
                        return Failure<TResponse>("invalid_api_response", "The backend returned an unreadable response.", request.responseCode);
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
