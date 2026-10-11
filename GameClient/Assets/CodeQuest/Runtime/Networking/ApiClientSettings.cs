using UnityEngine;

namespace CodeQuest.Networking
{
    [CreateAssetMenu(menuName = "CodeQuest/Networking/API Client Settings")]
    public sealed class ApiClientSettings : ScriptableObject
    {
        [SerializeField] private string baseUrl = "http://127.0.0.1:8000";
        [SerializeField, Min(1)] private int timeoutSeconds = 10;

        public string BaseUrl => (baseUrl ?? string.Empty).Trim().TrimEnd('/');
        public int TimeoutSeconds => Mathf.Max(1, timeoutSeconds);
    }
}
