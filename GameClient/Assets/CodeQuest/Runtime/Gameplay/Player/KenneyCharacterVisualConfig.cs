using UnityEngine;

namespace CodeQuest.Gameplay.Player
{
    [CreateAssetMenu(fileName = "KenneyCharacterVisualConfig", menuName = "CodeQuest/Kenney Character Visual Config")]
    public sealed class KenneyCharacterVisualConfig : ScriptableObject
    {
        public GameObject characterModel;
        public Avatar characterAvatar;
        public RuntimeAnimatorController animatorController;
        public Material humanMaleMaterial;
    }
}
