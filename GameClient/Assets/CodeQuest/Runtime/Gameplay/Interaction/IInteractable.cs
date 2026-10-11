using UnityEngine;

namespace CodeQuest.Gameplay.Interaction
{
    public interface IInteractable
    {
        string InteractionId { get; }
        string InteractionPrompt { get; }
        string UnavailableReason { get; }
        bool CanInteract { get; }
        bool IsAvailable { get; }
        int SelectionPriority { get; }
        void Interact(GameObject interactor);
    }

    public interface IInteractionSource
    {
        string CurrentPrompt { get; }
        bool TryInteract();
        void CancelCurrentInteraction();
    }

    public interface IInteractionCancellable
    {
        void CancelInteraction(GameObject interactor);
    }

    public abstract class InteractableBehaviour : MonoBehaviour, IInteractable
    {
        [SerializeField] private string interactionId;
        [SerializeField] private string interactionPrompt = "Interact";
        [SerializeField] private int selectionPriority;
        public string InteractionId => string.IsNullOrWhiteSpace(interactionId) ? gameObject.name : interactionId;
        public virtual string InteractionPrompt => interactionPrompt;
        public virtual string UnavailableReason => "Unavailable";
        public virtual bool CanInteract => true;
        public bool IsAvailable => CanInteract;
        public int SelectionPriority => selectionPriority;
        public void Configure(string id, string prompt, int priority = 0)
        {
            interactionId = id;
            interactionPrompt = prompt;
            selectionPriority = priority;
        }
        public abstract void Interact(GameObject interactor);
    }
}
