using System;
using System.Threading;
using System.Threading.Tasks;

namespace CodeQuest.Gameplay.Challenges
{
    public enum SubmissionStatus { Queued, Running, Passed, Failed, TimedOut, InternalError }

    [Serializable]
    public sealed class ChallengeReference
    {
        public string slug;
        public int version;
        public string objectiveSlug;
        public int objectiveVersion;
    }

    [Serializable]
    public sealed class SubmissionRequest
    {
        public string clientSubmissionId;
        public int challengeVersion;
        public string source;
    }

    [Serializable]
    public sealed class EvaluationResult
    {
        public SubmissionStatus status;
        public int scorePercent;
        public int passedTests;
        public int totalTests;
        public bool hasResult;
        public string[] diagnostics;
        public string createdAt;
        public string completedAt;
    }

    /// <summary>Future boundary only; implementations must call an isolated execution service, never run source in Unity or BackendAPI.</summary>
    public interface IChallengeSubmissionService
    {
        Task<EvaluationResult> SubmitAsync(SubmissionRequest request, CancellationToken cancellationToken);
    }
}
