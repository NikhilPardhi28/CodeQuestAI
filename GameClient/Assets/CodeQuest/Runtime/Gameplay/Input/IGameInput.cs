using UnityEngine;

namespace CodeQuest.Gameplay.Input
{
    public interface IGameInput
    {
        Vector2 Move { get; }
        Vector2 Look { get; }
        bool RunHeld { get; }
        bool JumpPressed { get; }
        bool InteractPressed { get; }
    }

    /// <summary>Uses Unity's built-in legacy input axes; replace behind IGameInput for controller rebinding.</summary>
    public sealed class LegacyGameInput : IGameInput
    {
        public Vector2 Move => new Vector2(UnityEngine.Input.GetAxisRaw("Horizontal"), UnityEngine.Input.GetAxisRaw("Vertical"));
        public Vector2 Look => new Vector2(UnityEngine.Input.GetAxis("Mouse X"), UnityEngine.Input.GetAxis("Mouse Y"));
        public bool RunHeld => UnityEngine.Input.GetKey(KeyCode.LeftShift) || UnityEngine.Input.GetKey(KeyCode.RightShift);
        public bool JumpPressed => UnityEngine.Input.GetButtonDown("Jump");
        public bool InteractPressed => UnityEngine.Input.GetKeyDown(KeyCode.E);
    }
}
