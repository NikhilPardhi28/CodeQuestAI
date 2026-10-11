using UnityEngine;
using UnityEngine.SceneManagement;

namespace CodeQuest.Core
{
    public interface ISceneTransitionService
    {
        bool TryLoad(string sceneName);
    }

    public sealed class SceneTransitionService : ISceneTransitionService
    {
        public bool TryLoad(string sceneName)
        {
            if (string.IsNullOrWhiteSpace(sceneName) || !Application.CanStreamedLevelBeLoaded(sceneName)) return false;
            SceneManager.LoadSceneAsync(sceneName);
            return true;
        }
    }
}
