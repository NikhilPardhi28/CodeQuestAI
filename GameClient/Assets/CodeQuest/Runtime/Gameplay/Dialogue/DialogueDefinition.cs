using System;
using UnityEngine;

namespace CodeQuest.Gameplay.Dialogue
{
    public enum DialogueConditionKind { Always, QuestActive, QuestCompleted, QuestNotStarted }

    [Serializable]
    public sealed class DialogueChoice
    {
        public string label;
        public string nextNodeId;
        public DialogueConditionKind condition;
        public string questId;
        public string acceptQuestSlug;
    }

    [Serializable]
    public sealed class DialogueNode
    {
        public string id;
        [TextArea(2, 5)] public string line;
        public DialogueChoice[] choices = Array.Empty<DialogueChoice>();
        public string eventId;
    }

    [CreateAssetMenu(menuName = "CodeQuest/Dialogue Definition")]
    public sealed class DialogueDefinition : ScriptableObject
    {
        public string npcId;
        public string entryNodeId;
        public DialogueNode[] nodes = Array.Empty<DialogueNode>();
        public DialogueNode Find(string id)
        {
            foreach (var node in nodes) if (node != null && node.id == id) return node;
            return null;
        }
    }

    public interface IDialogueConditions
    {
        bool IsQuestActive(string questId);
        bool IsQuestCompleted(string questId);
        bool IsQuestStarted(string questId);
    }

    public sealed class DialogueSession
    {
        private DialogueDefinition _definition;
        private readonly IDialogueConditions _conditions;
        public DialogueNode Current { get; private set; }
        public bool IsOpen => Current != null;
        public event Action<string> EventRaised;

        public DialogueSession(IDialogueConditions conditions) => _conditions = conditions;

        public bool Begin(DialogueDefinition definition)
        {
            _definition = definition;
            Current = definition == null ? null : definition.Find(definition.entryNodeId);
            RaiseNodeEvent();
            return Current != null;
        }

        public bool Choose(int visibleChoiceIndex)
        {
            if (Current == null) return false;
            var visible = VisibleChoices();
            if (visibleChoiceIndex < 0 || visibleChoiceIndex >= visible.Count) return false;
            Current = _definition.Find(visible[visibleChoiceIndex].nextNodeId);
            if (Current == null) { Cancel(); return false; }
            RaiseNodeEvent();
            return true;
        }

        public System.Collections.Generic.List<DialogueChoice> VisibleChoices()
        {
            var result = new System.Collections.Generic.List<DialogueChoice>();
            if (Current == null || Current.choices == null) return result;
            foreach (var choice in Current.choices)
            {
                if (choice == null) continue;
                var visible = choice.condition == DialogueConditionKind.Always ||
                    (choice.condition == DialogueConditionKind.QuestActive && _conditions != null && _conditions.IsQuestActive(choice.questId)) ||
                    (choice.condition == DialogueConditionKind.QuestCompleted && _conditions != null && _conditions.IsQuestCompleted(choice.questId)) ||
                    (choice.condition == DialogueConditionKind.QuestNotStarted && _conditions != null && !_conditions.IsQuestStarted(choice.questId));
                if (visible) result.Add(choice);
            }
            return result;
        }

        public void Cancel() => Current = null;

        private void RaiseNodeEvent()
        {
            if (!string.IsNullOrWhiteSpace(Current?.eventId)) EventRaised?.Invoke(Current.eventId);
        }
    }
}
