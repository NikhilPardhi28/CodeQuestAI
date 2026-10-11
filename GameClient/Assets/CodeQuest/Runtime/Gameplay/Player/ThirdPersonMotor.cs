using CodeQuest.Gameplay.Input;
using UnityEngine;

namespace CodeQuest.Gameplay.Player
{
    [RequireComponent(typeof(CharacterController))]
    public sealed class ThirdPersonMotor : MonoBehaviour
    {
        [SerializeField, Min(0f)] private float walkSpeed = 4f;
        [SerializeField, Min(0f)] private float runSpeed = 6.5f;
        [SerializeField, Min(0f)] private float jumpHeight = 1.2f;
        [SerializeField, Min(0f)] private float gravity = 20f;
        [SerializeField, Min(0f)] private float turnSmoothTime = 0.12f;
        private CharacterController _controller;
        private IGameInput _input;
        private Transform _orientation;
        private float _verticalVelocity;
        private float _turnVelocity;

        public void Initialize(IGameInput input, Transform cameraOrientation)
        {
            _input = input;
            _orientation = cameraOrientation;
        }

        private void Awake() => _controller = GetComponent<CharacterController>();

        private void Update()
        {
            if (_input == null || _orientation == null) return;
            var moveInput = MovementRules.ClampInput(_input.Move);
            var forward = Vector3.ProjectOnPlane(_orientation.forward, Vector3.up).normalized;
            var right = Vector3.ProjectOnPlane(_orientation.right, Vector3.up).normalized;
            var direction = forward * moveInput.y + right * moveInput.x;
            if (direction.sqrMagnitude > 0.001f)
            {
                var targetAngle = Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;
                transform.rotation = Quaternion.Euler(0f, Mathf.SmoothDampAngle(
                    transform.eulerAngles.y, targetAngle, ref _turnVelocity, turnSmoothTime), 0f);
            }

            if (_controller.isGrounded)
            {
                if (_verticalVelocity < 0f) _verticalVelocity = -2f;
                if (_input.JumpPressed) _verticalVelocity = MovementRules.JumpVelocity(jumpHeight, gravity);
            }
            _verticalVelocity -= gravity * Time.deltaTime;
            var speed = MovementRules.SelectSpeed(_input.RunHeld, walkSpeed, runSpeed);
            var displacement = direction * speed + Vector3.up * _verticalVelocity;
            _controller.Move(displacement * Time.deltaTime);
        }
    }
}
