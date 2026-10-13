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
        private Animator _animator;
        private static readonly int SpeedParam = Animator.StringToHash("Speed");
        private static readonly int JumpParam = Animator.StringToHash("Jump");
        private static readonly int IsGroundedParam = Animator.StringToHash("IsGrounded");

        public void Initialize(IGameInput input, Transform cameraOrientation)
        {
            _input = input;
            _orientation = cameraOrientation;
        }

        public void BindAnimator(Animator animator)
        {
            _animator = animator;
        }

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            if (_animator == null) _animator = GetComponentInChildren<Animator>();
        }

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

            var jumpedThisFrame = false;
            if (_controller.isGrounded)
            {
                if (_verticalVelocity < 0f) _verticalVelocity = -2f;
                if (_input.JumpPressed)
                {
                    _verticalVelocity = MovementRules.JumpVelocity(jumpHeight, gravity);
                    jumpedThisFrame = true;
                }
            }
            _verticalVelocity -= gravity * Time.deltaTime;
            var speed = MovementRules.SelectSpeed(_input.RunHeld, walkSpeed, runSpeed);
            var displacement = direction * speed + Vector3.up * _verticalVelocity;
            _controller.Move(displacement * Time.deltaTime);

            if (_animator != null)
            {
                var horizontalSpeed = direction.sqrMagnitude > 0.001f ? speed : 0f;
                _animator.SetFloat(SpeedParam, horizontalSpeed);
                _animator.SetBool(IsGroundedParam, _controller.isGrounded);
                if (jumpedThisFrame) _animator.SetTrigger(JumpParam);
            }
        }
    }
}
