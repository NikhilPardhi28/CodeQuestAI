using CodeQuest.Gameplay.Input;
using UnityEngine;

namespace CodeQuest.Gameplay.Interaction
{
    public sealed class PlayerInteractor : MonoBehaviour, IInteractionSource
    {
        [SerializeField, Min(0.1f)] private float range = 2.5f;
        [SerializeField] private LayerMask interactionMask = ~0;
        private IGameInput _input;
        private IInteractable _current;
        public string CurrentPrompt => _current != null && _current.CanInteract ? _current.InteractionPrompt : string.Empty;

        public void Initialize(IGameInput input) => _input = input;

        private void Update()
        {
            _current = FindClosest();
            if (_input != null && _input.InteractPressed) TryInteract();
        }

        public bool TryInteract()
        {
            if (_current == null || !_current.CanInteract) return false;
            _current.Interact(gameObject);
            return true;
        }

        private IInteractable FindClosest()
        {
            var hits = Physics.OverlapSphere(transform.position, range, interactionMask, QueryTriggerInteraction.Collide);
            IInteractable nearest = null;
            var bestDistance = float.MaxValue;
            foreach (var hit in hits)
            {
                if (hit.transform == transform || hit.transform.IsChildOf(transform)) continue;
                var candidates = hit.GetComponentsInParent<MonoBehaviour>();
                foreach (var candidate in candidates)
                {
                    if (!(candidate is IInteractable interactable) || !interactable.CanInteract) continue;
                    var distance = (candidate.transform.position - transform.position).sqrMagnitude;
                    if (distance >= bestDistance) continue;
                    bestDistance = distance;
                    nearest = interactable;
                }
            }
            return nearest;
        }
    }
}
