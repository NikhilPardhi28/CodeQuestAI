using System;
using System.Collections.Generic;
using CodeQuest.Gameplay.Quests;

namespace CodeQuest.Networking
{
    [Serializable] public sealed class ApiErrorDto
    {
        public string code;
        public string message;
        public bool retryable;
        public string correlationId;
        public QuestProgressDto currentState;
    }

    [Serializable] public sealed class HealthDto { public string status; }
    [Serializable] public sealed class ReadinessChecksDto { public string database; }
    [Serializable] public sealed class ReadinessDto { public string status; public ReadinessChecksDto checks; }

    [Serializable] public sealed class PageDto<T>
    {
        public List<T> items;
        public int limit;
        public int offset;
        public int total;
    }

    [Serializable] public sealed class RegionDto
    {
        public string slug;
        public int version;
        public string name;
        public string summary;
        public int sortOrder;
        public string unlockRegionSlug;
    }

    [Serializable] public sealed class ObjectiveDto
    {
        public string slug;
        public int version;
        public string regionSlug;
        public int regionVersion;
        public string title;
        public string summary;
        public int sortOrder;
        public string[] prerequisites;
    }

    [Serializable] public sealed class QuestDto
    {
        public string slug;
        public int version;
        public string regionSlug;
        public int regionVersion;
        public string objectiveSlug;
        public int objectiveVersion;
        public string title;
        public string summary;
        public QuestContentDto publicContent;
    }

    [Serializable] public sealed class QuestContentDto
    {
        public string kind;
        public int estimatedMinutes;
    }

    [Serializable] public sealed class ChallengeDto
    {
        public string slug;
        public int version;
        public string objectiveSlug;
        public int objectiveVersion;
        public string title;
        public string statement;
        public ChallengeContentDto publicContent;
    }

    [Serializable] public sealed class ChallengeContentDto
    {
        public string mode;
        public string functionName;
        public string functionSignature;
        public string starterCode;
        public string[] examples;
        public string[] visibleHints;
        public string expectedOutputFormat;
    }

    [Serializable] public sealed class ChallengeSubmissionRequestDto
    {
        public string clientSubmissionId;
        public int challengeVersion;
        public string source;
    }

    [Serializable] public sealed class ChallengeHintDto
    {
        public string challengeSlug;
        public int challengeVersion;
        public int level;
        public string content;
    }

    [Serializable] public sealed class SubmissionResultDto
    {
        public int scorePercent;
        public int passedTests;
        public int totalTests;
        public bool hasResult;
        public SubmissionVisibleResultDto[] visibleResults;
        public SubmissionDiagnosticDto[] diagnostics;
    }

    [Serializable] public sealed class SubmissionVisibleResultDto
    {
        public bool passed;
        public string diagnosticCode;
        public string message;
    }

    [Serializable] public sealed class SubmissionDiagnosticDto
    {
        public string code;
        public string message;
    }

    [Serializable] public sealed class ChallengeSubmissionDto
    {
        public string id;
        public string challengeSlug;
        public int challengeVersion;
        public string clientSubmissionId;
        public string status;
        public SubmissionResultDto result;
        public string createdAt;
        public string completedAt;
    }

    [Serializable] public sealed class PlayerProfileDto
    {
        public string id;
        public string displayName;
        public string locale;
        public string createdAt;
        public string updatedAt;
    }

    [Serializable] public sealed class PlayerProfileUpsertDto
    {
        public string displayName;
        public string locale;
    }

    [Serializable] public sealed class QuestProgressDto
    {
        public string questSlug;
        public int questVersion;
        public string status;
        public int revision;
        public QuestObjectiveProgressDto[] objectiveProgress;
        public string createdAt;
        public string updatedAt;
    }

    [Serializable] public sealed class ProgressionDto
    {
        public int experience;
        public int level;
        public int revision;
        public string updatedAt;
    }

    [Serializable] public sealed class AchievementAwardDto
    {
        public string achievementSlug;
        public int achievementVersion;
        public string awardedAt;
        public string source;
    }

    [Serializable] public sealed class SubmissionMetadataDto
    {
        public string id;
        public string challengeSlug;
        public int challengeVersion;
        public string clientSubmissionId;
        public string status;
        public string sourceDigest;
        public string createdAt;
        public string completedAt;
    }

    [Serializable] public sealed class QuestObjectiveProgressDto
    {
        public string objectiveId;
        public int completedCount;
        public int requiredCount;
        public bool completed;
    }
}
