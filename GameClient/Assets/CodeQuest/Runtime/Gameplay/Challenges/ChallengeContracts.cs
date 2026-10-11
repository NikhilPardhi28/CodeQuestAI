using System;
using System.Threading;
using System.Threading.Tasks;

namespace CodeQuest.Gameplay.Challenges
{
    public enum SubmissionStatus { Queued, Running, Passed, Failed, TimedOut, InternalError }
    public enum ChallengeErrorCategory { None, Syntax, Runtime, WrongAnswer, Timeout, Network }

    public static class ChallengeStatusRules
    {
        public static SubmissionStatus FromServer(string status) => status switch
        {
            "queued" => SubmissionStatus.Queued,
            "running" => SubmissionStatus.Running,
            "passed" => SubmissionStatus.Passed,
            "failed" => SubmissionStatus.Failed,
            "timed_out" => SubmissionStatus.TimedOut,
            _ => SubmissionStatus.InternalError
        };

        public static bool IsTerminal(SubmissionStatus status) => status == SubmissionStatus.Passed ||
            status == SubmissionStatus.Failed || status == SubmissionStatus.TimedOut ||
            status == SubmissionStatus.InternalError;

        public static bool IsConfirmedPass(SubmissionStatus status) => status == SubmissionStatus.Passed;
    }

    public sealed class TutorHintContext
    {
        public string[] PublishedHints;
        public int HintLevel;
        public int CompletedChallenges;
        public ChallengeErrorCategory LastError;
    }

    public interface ITutorHintProvider
    {
        string GetHint(TutorHintContext context);
    }

    /// <summary>Uses public catalog hints only; learner source and personal data never leave the client.</summary>
    public sealed class RuleBasedTutorHintProvider : ITutorHintProvider
    {
        public string GetHint(TutorHintContext context)
        {
            if (context == null) return "Look at the input values and decide what result the function should return.";
            var level = Math.Max(1, context.HintLevel);
            var hints = context.PublishedHints ?? Array.Empty<string>();
            var hint = hints.Length == 0 ? Fallback(level) : hints[Math.Min(level - 1, hints.Length - 1)];
            var response = context.LastError switch
            {
                ChallengeErrorCategory.Syntax => "Check the function header, indentation, and punctuation. ",
                ChallengeErrorCategory.Runtime => "Check how the function handles each input value. ",
                ChallengeErrorCategory.WrongAnswer => "Compare the required output carefully, including spaces and value types. ",
                ChallengeErrorCategory.Timeout => "Keep the solution simple and avoid unnecessary repetition. ",
                ChallengeErrorCategory.Network => "Your code was not evaluated because the service is unavailable. Retry when connected. ",
                _ => string.Empty
            };
            if (context.CompletedChallenges > 0 && level == 1)
                response += "Use the same step-by-step approach that worked in an earlier challenge. ";
            return response + hint;
        }

        private static string Fallback(int level) => level switch
        {
            1 => "Identify the values the function receives and the value it must return.",
            2 => "Store an intermediate value with a descriptive variable name.",
            _ => "Build the result from the input variables, then return it."
        };
    }

    public static class ChallengeEditorRules
    {
        /// <summary>Checks only the required function declaration; it never parses or executes learner code.</summary>
        public static bool HasExpectedFunctionHeader(string source, string functionName)
        {
            if (string.IsNullOrWhiteSpace(source) || string.IsNullOrWhiteSpace(functionName)) return false;
            var expected = "def " + functionName + "(";
            foreach (var rawLine in source.Split('\n'))
                if (rawLine.TrimStart().StartsWith(expected, StringComparison.Ordinal)) return true;
            return false;
        }
    }

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
