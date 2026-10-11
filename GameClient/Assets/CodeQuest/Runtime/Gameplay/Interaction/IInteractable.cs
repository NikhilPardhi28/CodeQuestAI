using UnityEngine;

namespace CodeQuest.Gameplay.Interaction
{
    public interface IInteractable
    {
        string InteractionPrompt { get; }
        bool CanInteract { get; }
        void Interact(GameObject interactor);
    }

    public interface IInteractionSource
    {
        string CurrentPrompt { get; }
        bool TryInteract();
    }
}
