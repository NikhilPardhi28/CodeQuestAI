using System;
using System.Collections.Generic;

namespace CodeQuest.Networking
{
    [Serializable] public sealed class ApiErrorDto
    {
        public string code;
        public string message;
        public bool retryable;
        public string correlationId;
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
        public string[] examples;
        public string[] visibleHints;
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
}
