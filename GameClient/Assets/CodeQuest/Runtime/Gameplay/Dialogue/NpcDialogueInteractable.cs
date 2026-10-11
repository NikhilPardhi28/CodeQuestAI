using CodeQuest.Gameplay.Interaction;
using UnityEngine;

namespace CodeQuest.Gameplay.Dialogue
{
    public sealed class NpcDialogueInteractable : InteractableBehaviour
    {
        [SerializeField] private DialogueDefinition dialogue;
        public DialogueDefinition Definition => dialogue;
        public void Initialize(DialogueDefinition definition) => dialogue = definition;
        public override string InteractionPrompt => "Talk to " + (dialogue == null ? gameObject.name : dialogue.npcId);
        public override bool CanInteract => dialogue != null;
        public override string UnavailableReason => "Dialogue unavailable";
        public override void Interact(GameObject interactor) { }
    }
}
