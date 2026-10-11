using System;
using System.Threading;
using System.Threading.Tasks;

namespace CodeQuest.Gameplay.Challenges
{
    public enum SubmissionStatus { Received, Queued, Running, Passed, Failed, Error }

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
        public ChallengeReference challenge;
        public string source;
    }

    [Serializable]
    public sealed class EvaluationResult
    {
        public SubmissionStatus status;
        public string summary;
        public string[] hints;
        public string learningObjective;
    }

    /// <summary>Future boundary only; implementations must call an isolated execution service, never run source in Unity or BackendAPI.</summary>
    public interface IChallengeSubmissionService
    {
        Task<EvaluationResult> SubmitAsync(SubmissionRequest request, CancellationToken cancellationToken);
    }
}
