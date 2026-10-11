using UnityEngine;

namespace CodeQuest.Gameplay.Player
{
    public static class MovementRules
    {
        public static Vector2 ClampInput(Vector2 input) => Vector2.ClampMagnitude(input, 1f);

        public static float SelectSpeed(bool running, float walkSpeed, float runSpeed) =>
            Mathf.Max(0f, running ? runSpeed : walkSpeed);

        public static float JumpVelocity(float jumpHeight, float gravityMagnitude) =>
            Mathf.Sqrt(Mathf.Max(0f, 2f * jumpHeight * gravityMagnitude));
    }
}
