using CodeQuest.Core;
using CodeQuest.Gameplay.Camera;
using CodeQuest.Gameplay.Input;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Gameplay.Dialogue;
using CodeQuest.Gameplay.Player;
using CodeQuest.Gameplay.Quests;
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
            var quests = new QuestService(api);
            QuestRuntime.Service = quests;
            CreateSampleHub(quests);
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
            _hud = new RuntimeHud(api, _gameState, interactor, quests, transform);
            _gameState.ChangeTo(GameState.MainMenu);
        }

        private void CreateSampleHub(QuestService quests)
        {
            var quest = ScriptableObject.CreateInstance<QuestDefinition>();
            quest.questId = "light-the-signal";
            quest.version = 2;
            quest.category = QuestCategory.Main;
            quest.title = "The Signal Keeper";
            quest.summary = "Activate the registered relay and complete the server-authored signal objectives.";
            quest.objectives = new[]
            {
                new QuestObjectiveDefinition { id = "activate-relay", description = "Activate the relay switch", kind = QuestObjectiveKind.Interact, targetId = "relay-switch", targetCount = 1 },
                new QuestObjectiveDefinition { id = "reach-platform", description = "Reach the signal platform", kind = QuestObjectiveKind.Checkpoint, targetId = "signal-platform", targetCount = 1 },
                new QuestObjectiveDefinition { id = "pass-signal-challenge", description = "Complete the signal coding challenge", kind = QuestObjectiveKind.ChallengePassed, targetId = "signal-coordinate", targetVersion = 2, targetCount = 1 }
            };
            quests.Register(quest);
            quests.Activate(quest.questId);

            var dialogue = ScriptableObject.CreateInstance<DialogueDefinition>();
            dialogue.npcId = "Signal Keeper";
            dialogue.entryNodeId = "greeting";
            dialogue.nodes = new[]
            {
                new DialogueNode
                {
                    id = "greeting", line = "The relay is quiet. Would you help me check its switch?", eventId = "keeper-greeting",
                    choices = new[] { new DialogueChoice { label = "I will inspect the relay.", nextNodeId = "thanks" }, new DialogueChoice { label = "Goodbye.", nextNodeId = "farewell" } }
                },
                new DialogueNode { id = "thanks", line = "Thank you. The switch is just outside the station." },
                new DialogueNode { id = "farewell", line = "Safe travels." }
            };

            var npc = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            npc.name = "Signal Keeper NPC";
            npc.transform.position = new Vector3(2f, 1f, 2f);
            npc.AddComponent<NpcDialogueInteractable>().Initialize(dialogue);
            var switchObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
            switchObject.name = "Relay Switch";
            switchObject.transform.position = new Vector3(-2f, .5f, 2f);
            switchObject.AddComponent<SwitchInteractable>().Configure("relay-switch", quest.questId, "relay-switch", QuestObjectiveKind.Interact);
            var platform = GameObject.CreatePrimitive(PrimitiveType.Cube);
            platform.name = "Signal Platform Checkpoint";
            platform.transform.position = new Vector3(0f, .25f, 5f);
            platform.AddComponent<CheckpointInteractable>().Configure("signal-platform", quest.questId, "signal-platform", QuestObjectiveKind.Checkpoint);
        }

        private ThirdPersonMotor CreatePlayerAndCamera(out ThirdPersonCameraRig cameraRig)
        {
            if (GameObject.Find("Greybox Ground") == null)
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
