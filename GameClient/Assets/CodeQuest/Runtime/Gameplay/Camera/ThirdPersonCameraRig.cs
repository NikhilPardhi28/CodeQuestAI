using CodeQuest.Gameplay.Input;
using UnityEngine;

namespace CodeQuest.Gameplay.Camera
{
    public sealed class ThirdPersonCameraRig : MonoBehaviour
    {
        [SerializeField] private Vector3 targetOffset = new Vector3(0f, 1.4f, 0f);
        [SerializeField, Min(0.1f)] private float distance = 4.2f;
        [SerializeField, Min(0f)] private float followSharpness = 14f;
        [SerializeField, Min(0f)] private float lookSensitivity = 2.2f;
        [SerializeField] private Vector2 pitchLimits = new Vector2(-20f, 65f);
        [SerializeField] private LayerMask collisionMask = ~0;
        [SerializeField, Min(0.01f)] private float collisionRadius = 0.25f;
        private Transform _target;
        private IGameInput _input;
        private float _yaw;
        private float _pitch = 14f;

        public void Initialize(Transform target, IGameInput input)
        {
            _target = target;
            _input = input;
            _yaw = target.eulerAngles.y;
        }

        public void Configure(Vector3 offset, float camDistance, float sensitivity)
        {
            targetOffset = offset;
            distance = camDistance;
            lookSensitivity = sensitivity;
        }

        private void LateUpdate()
        {
            if (_target == null || _input == null) return;
            var look = _input.Look;
            _yaw += look.x * lookSensitivity;
            _pitch = Mathf.Clamp(_pitch - look.y * lookSensitivity, pitchLimits.x, pitchLimits.y);
            var rotation = Quaternion.Euler(_pitch, _yaw, 0f);
            var pivot = _target.position + targetOffset;
            var desired = pivot - rotation * Vector3.forward * distance;
            var direction = desired - pivot;
            if (Physics.SphereCast(pivot, collisionRadius, direction.normalized, out var hit,
                    direction.magnitude, collisionMask, QueryTriggerInteraction.Ignore))
            {
                var safeDistance = Mathf.Max(0.2f, hit.distance - collisionRadius);
                desired = pivot + direction.normalized * safeDistance;
            }
            var blend = 1f - Mathf.Exp(-followSharpness * Time.deltaTime);
            transform.position = Vector3.Lerp(transform.position, desired, blend);
            transform.rotation = rotation;
        }
    }
}
