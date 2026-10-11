using System;
using System.Collections.Generic;
using CodeQuest.Gameplay.Quests;
using UnityEngine;

namespace CodeQuest.Gameplay.Interaction
{
    public abstract class StatefulWorldInteractable : InteractableBehaviour
    {
        [SerializeField] private string questId;
        [SerializeField] private QuestObjectiveKind questEventKind = QuestObjectiveKind.Interact;
        [SerializeField] private string questTargetId;
        private int _eventSequence;
        public event Action<StatefulWorldInteractable> Used;
        protected void EmitUsed()
        {
            Used?.Invoke(this);
            if (QuestRuntime.Service != null && !string.IsNullOrWhiteSpace(questId))
                QuestRuntime.Service.RecordEvent(questId, InteractionId + ":" + (++_eventSequence), questEventKind, questTargetId);
        }
        protected string TargetId => questTargetId;
        public void Configure(string id, string questId, string target, QuestObjectiveKind kind)
        {
            base.Configure(id, id);
            this.questId = questId;
            questTargetId = target;
            questEventKind = kind;
        }
    }

    public sealed class DoorInteractable : StatefulWorldInteractable
    {
        [SerializeField] private Transform door;
        [SerializeField] private Vector3 openOffset = new Vector3(0f, 2f, 0f);
        private bool _open;
        public override string InteractionPrompt => _open ? "Close door" : "Open door";
        public override void Interact(GameObject interactor)
        {
            _open = !_open;
            if (door != null) door.localPosition += _open ? openOffset : -openOffset;
            EmitUsed();
        }
    }

    public sealed class SwitchInteractable : StatefulWorldInteractable
    {
        private bool _on;
        public event Action<bool> StateChanged;
        public override string InteractionPrompt => _on ? "Turn switch off" : "Activate switch";
        public override void Interact(GameObject interactor) { _on = !_on; StateChanged?.Invoke(_on); EmitUsed(); }
    }

    public sealed class CheckpointInteractable : StatefulWorldInteractable
    {
        public static Vector3? LastLocalCheckpoint { get; private set; }
        public override string InteractionPrompt => "Set checkpoint (local)";
        public override void Interact(GameObject interactor)
        {
            LastLocalCheckpoint = transform.position;
            if (interactor != null) interactor.transform.position = transform.position;
            EmitUsed();
        }
    }

    public sealed class TreasureChestInteractable : StatefulWorldInteractable
    {
        [SerializeField] private string cosmeticRewardId;
        private bool _opened;
        public override bool CanInteract => !_opened;
        public override string UnavailableReason => "Chest already opened (reward not claimed)";
        public override string InteractionPrompt => "Open chest";
        public override void Interact(GameObject interactor)
        {
            if (_opened) return;
            _opened = true;
            Debug.Log("Local chest opened. Any persistent reward requires server validation: " + cosmeticRewardId, this);
            EmitUsed();
        }
    }
}
