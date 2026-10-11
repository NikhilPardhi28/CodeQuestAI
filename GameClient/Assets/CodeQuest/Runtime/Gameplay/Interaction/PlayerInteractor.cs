using System;
using System.Collections.Generic;
using System.Text;
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
        private readonly List<IInteractable> _targets = new List<IInteractable>();
        public string CurrentPrompt => _current == null ? string.Empty : _current.IsAvailable ? _current.InteractionPrompt : _current.UnavailableReason;
        public IInteractable CurrentTarget => _current;
        public event Action<IInteractable> TargetChanged;
        public event Action<IInteractable> InteractionStarted;
        public event Action<IInteractable> InteractionCompleted;
        public event Action<IInteractable> InteractionCanceled;

        public void Initialize(IGameInput input) => _input = input;

        private void Update()
        {
            SetTarget(FindTarget());
            if (_input != null && _input.InteractPressed) TryInteract();
        }

        public bool TryInteract()
        {
            if (_current == null || !_current.IsAvailable) return false;
            var target = _current;
            InteractionStarted?.Invoke(target);
            try
            {
                target.Interact(gameObject);
                InteractionCompleted?.Invoke(target);
                return true;
            }
            catch (OperationCanceledException)
            {
                InteractionCanceled?.Invoke(target);
                return false;
            }
        }

        public void CancelCurrentInteraction()
        {
            if (_current == null) return;
            if (_current is IInteractionCancellable cancellable) cancellable.CancelInteraction(gameObject);
            InteractionCanceled?.Invoke(_current);
        }

        private void SetTarget(IInteractable target)
        {
            if (ReferenceEquals(_current, target)) return;
            _current = target;
            TargetChanged?.Invoke(target);
        }

        private IInteractable FindTarget()
        {
            var hits = Physics.OverlapSphere(transform.position, range, interactionMask, QueryTriggerInteraction.Collide);
            _targets.Clear();
            foreach (var hit in hits)
            {
                if (hit.transform == transform || hit.transform.IsChildOf(transform)) continue;
                foreach (var candidate in hit.GetComponentsInParent<MonoBehaviour>())
                    if (candidate is IInteractable interactable && !_targets.Contains(interactable)) _targets.Add(interactable);
            }
            _targets.Sort((left, right) => InteractionTargetSelector.Compare(left, right, transform.position));
            return _targets.Count == 0 ? null : _targets[0];
        }
    }

    public static class InteractionTargetSelector
    {
        public static int Compare(IInteractable left, IInteractable right, Vector3 origin)
        {
            var distance = Distance(left, origin).CompareTo(Distance(right, origin));
            if (distance != 0) return distance;
            var priority = right.SelectionPriority.CompareTo(left.SelectionPriority);
            if (priority != 0) return priority;
            var id = string.CompareOrdinal(left.InteractionId, right.InteractionId);
            if (id != 0) return id;
            var hierarchy = string.CompareOrdinal(HierarchyPath(left), HierarchyPath(right));
            if (hierarchy != 0) return hierarchy;
            return string.CompareOrdinal((left as Component)?.GetType().FullName, (right as Component)?.GetType().FullName);
        }

        private static string HierarchyPath(IInteractable target)
        {
            var component = target as Component;
            if (component == null) return string.Empty;
            var builder = new StringBuilder();
            for (var current = component.transform; current != null; current = current.parent)
                builder.Insert(0, "/" + current.GetSiblingIndex().ToString("D4") + ":" + current.name);
            return builder.ToString();
        }

        private static float Distance(IInteractable target, Vector3 origin)
        {
            var behaviour = target as Component;
            return behaviour == null ? float.MaxValue : (behaviour.transform.position - origin).sqrMagnitude;
        }
    }
}
