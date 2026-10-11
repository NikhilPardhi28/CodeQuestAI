using CodeQuest.Core;
using CodeQuest.Gameplay.Camera;
using CodeQuest.Gameplay.Input;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Gameplay.Player;
using CodeQuest.Networking;
using UnityEngine;

namespace CodeQuest.UI
{
    public sealed class CodeQuestBootstrap : MonoBehaviour
    {
        private GameStateService _gameState;
        private LegacyGameInput _input;
        private RuntimeHud _hud;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void EnsureBootstrap()
        {
            if (FindObjectOfType<CodeQuestBootstrap>() != null) return;
            new GameObject("CodeQuest Bootstrap").AddComponent<CodeQuestBootstrap>();
        }

        private void Awake()
        {
            var existing = FindObjectOfType<CodeQuestBootstrap>();
            if (existing != null && existing != this)
            {
                Destroy(gameObject);
                return;
            }
            DontDestroyOnLoad(gameObject);
            _gameState = new GameStateService();
            _input = new LegacyGameInput();
            var apiSettings = Resources.Load<ApiClientSettings>("ApiClientSettings");
            if (apiSettings == null) apiSettings = ScriptableObject.CreateInstance<ApiClientSettings>();
            var api = new CodeQuestApiClient(apiSettings, new UnauthenticatedTokenProvider());
            var player = FindObjectOfType<ThirdPersonMotor>();
            ThirdPersonCameraRig cameraRig;
            if (player == null) player = CreatePlayerAndCamera(out cameraRig);
            else
            {
                cameraRig = FindObjectOfType<ThirdPersonCameraRig>();
                if (cameraRig == null) cameraRig = CreateCamera(player.transform);
            }
            player.Initialize(_input, cameraRig.transform);
            cameraRig.Initialize(player.transform, _input);
            var interactor = player.GetComponent<PlayerInteractor>();
            if (interactor == null) interactor = player.gameObject.AddComponent<PlayerInteractor>();
            interactor.Initialize(_input);
            _hud = new RuntimeHud(api, _gameState, interactor, transform);
            _gameState.ChangeTo(GameState.MainMenu);
        }

        private ThirdPersonMotor CreatePlayerAndCamera(out ThirdPersonCameraRig cameraRig)
        {
            if (FindObjectOfType<Collider>() == null)
            {
                var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
                floor.name = "Greybox Ground";
                floor.transform.localScale = new Vector3(4f, 1f, 4f);
            }
            var playerObject = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            playerObject.name = "Player";
            playerObject.transform.position = new Vector3(0f, 1f, 0f);
            var visualCollider = playerObject.GetComponent<CapsuleCollider>();
            if (visualCollider != null) Destroy(visualCollider);
            playerObject.AddComponent<CharacterController>();
            var motor = playerObject.AddComponent<ThirdPersonMotor>();
            playerObject.AddComponent<PlayerInteractor>();
            cameraRig = CreateCamera(playerObject.transform);
            return motor;
        }

        private ThirdPersonCameraRig CreateCamera(Transform target)
        {
            var cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            var camera = cameraObject.AddComponent<UnityEngine.Camera>();
            camera.fieldOfView = 60f;
            cameraObject.AddComponent<AudioListener>();
            return cameraObject.AddComponent<ThirdPersonCameraRig>();
        }

        private void Update()
        {
            _hud?.Tick();
            if (UnityEngine.Input.GetKeyDown(KeyCode.Escape)) _hud.ToggleMenu();
        }

        private void OnDestroy()
        {
            if (_hud != null) _hud.Dispose();
        }
    }
}
