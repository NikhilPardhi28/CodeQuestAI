using System;
using System.Collections.Generic;
using UnityEngine;

namespace CodeQuest.Gameplay.Quests
{
    public enum QuestCategory { Main, Side }
    public enum QuestStatus { Locked, Available, Active, Completed, Failed }
    public enum QuestObjectiveKind { Interact, DialogueEvent, ChallengePassed, Checkpoint }
    public enum QuestRewardKind { Cosmetic, Experience, Item }

    [Serializable]
    public sealed class QuestObjectiveDefinition
    {
        public string id;
        public string description;
        public QuestObjectiveKind kind;
        public string targetId;
        [Min(1)] public int targetCount = 1;
    }

    [Serializable]
    public sealed class QuestRewardDefinition
    {
        public QuestRewardKind kind;
        public string rewardId;
        [Min(0)] public int quantity;
    }

    [CreateAssetMenu(menuName = "CodeQuest/Quest Definition")]
    public sealed class QuestDefinition : ScriptableObject
    {
        public string questId;
        [Min(1)] public int version = 1;
        public QuestCategory category;
        public string title;
        [TextArea] public string summary;
        public string[] prerequisites = Array.Empty<string>();
        public QuestObjectiveDefinition[] objectives = Array.Empty<QuestObjectiveDefinition>();
        public QuestRewardDefinition[] rewards = Array.Empty<QuestRewardDefinition>();

        public bool IsValid(out string error)
        {
            if (string.IsNullOrWhiteSpace(questId) || version < 1 || objectives == null || objectives.Length == 0)
            { error = "Quest ID, positive version, and at least one objective are required."; return false; }
            var objectiveIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var objective in objectives)
                if (objective == null || string.IsNullOrWhiteSpace(objective.id) || objective.targetCount < 1)
                { error = "Every objective needs an ID and positive target count."; return false; }
                else if (!objectiveIds.Add(objective.id))
                { error = "Objective IDs must be unique within a quest version."; return false; }
            foreach (var prerequisite in prerequisites ?? Array.Empty<string>())
                if (string.IsNullOrWhiteSpace(prerequisite) || prerequisite == questId)
                { error = "Prerequisites must name another quest."; return false; }
            foreach (var reward in rewards ?? Array.Empty<QuestRewardDefinition>())
                if (reward == null || string.IsNullOrWhiteSpace(reward.rewardId) || reward.quantity < 0)
                { error = "Rewards need an ID and non-negative quantity."; return false; }
            error = null;
            return true;
        }
    }
}
