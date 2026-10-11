using CodeQuest.Core;
using CodeQuest.Gameplay.Camera;
using CodeQuest.Gameplay.Input;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Gameplay.Dialogue;
using CodeQuest.Gameplay.Player;
using CodeQuest.Gameplay.Quests;
using CodeQuest.Networking;
using System;
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
            CreateVariableValley(quests);
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
            npc.transform.position = new Vector3(-4f, 1f, 2f);
            npc.AddComponent<NpcDialogueInteractable>().Initialize(dialogue);
            var switchObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
            switchObject.name = "Relay Switch";
            switchObject.transform.position = new Vector3(-6f, .5f, 2f);
            switchObject.AddComponent<SwitchInteractable>().Configure("relay-switch", quest.questId, "relay-switch", QuestObjectiveKind.Interact);
            var platform = GameObject.CreatePrimitive(PrimitiveType.Cube);
            platform.name = "Signal Platform Checkpoint";
            platform.transform.position = new Vector3(-4f, .25f, 5f);
            platform.AddComponent<CheckpointInteractable>().Configure("signal-platform", quest.questId, "signal-platform", QuestObjectiveKind.Checkpoint);
        }

        private void CreateVariableValley(QuestService quests)
        {
            var quest = ScriptableObject.CreateInstance<QuestDefinition>();
            quest.questId = "variables-in-the-valley";
            quest.version = 1;
            quest.category = QuestCategory.Main;
            quest.title = "A Message for the Valley";
            quest.summary = "Help Mira restore the beacon with five variable and input/output challenges.";
            quest.objectives = new[]
            {
                new QuestObjectiveDefinition { id = "accept-valley-quest", description = "Accept Mira's beacon quest", kind = QuestObjectiveKind.Interact, targetId = "valley-mentor" },
                new QuestObjectiveDefinition { id = "complete-valley-name-tag", description = "Create a greeting with a variable", kind = QuestObjectiveKind.ChallengePassed, targetId = "valley-name-tag" },
                new QuestObjectiveDefinition { id = "complete-valley-sunplot-area", description = "Calculate and store the sunplot area", kind = QuestObjectiveKind.ChallengePassed, targetId = "valley-sunplot-area" },
                new QuestObjectiveDefinition { id = "complete-valley-signal-label", description = "Format a numeric signal as text", kind = QuestObjectiveKind.ChallengePassed, targetId = "valley-signal-label" },
                new QuestObjectiveDefinition { id = "complete-valley-seed-count", description = "Return a total from repeated input values", kind = QuestObjectiveKind.ChallengePassed, targetId = "valley-seed-count" },
                new QuestObjectiveDefinition { id = "complete-valley-beacon-message", description = "Restore the final beacon message", kind = QuestObjectiveKind.ChallengePassed, targetId = "valley-beacon-message" }
            };
            quests.Register(quest);

            var dialogue = ScriptableObject.CreateInstance<DialogueDefinition>();
            dialogue.npcId = "Mira, Valley Guide";
            dialogue.entryNodeId = "greeting";
            dialogue.nodes = new[]
            {
                new DialogueNode
                {
                    id = "greeting",
                    line = "Welcome to Variable Valley. The beacon needs five simple messages. We will practice storing inputs and returning useful output.",
                    choices = new[]
                    {
                        new DialogueChoice { label = "I accept the beacon quest.", nextNodeId = "accepted", condition = DialogueConditionKind.QuestNotStarted, questId = quest.questId, acceptQuestSlug = quest.questId },
                        new DialogueChoice { label = "Let's continue the lessons.", nextNodeId = "active", condition = DialogueConditionKind.QuestActive, questId = quest.questId },
                        new DialogueChoice { label = "The beacon is restored!", nextNodeId = "complete", condition = DialogueConditionKind.QuestCompleted, questId = quest.questId },
                        new DialogueChoice { label = "Tell me about the region.", nextNodeId = "region" }
                    }
                },
                new DialogueNode { id = "accepted", line = "Thank you! The glowing gate leads to your first challenge. Your quest state will show as pending until the server confirms it." },
                new DialogueNode { id = "active", line = "Your next challenge is marked in the journal. The gate opens the ordered challenge list." },
                new DialogueNode { id = "complete", line = "You restored the beacon. Your XP and completed quest are confirmed by the backend." },
                new DialogueNode { id = "region", line = "Variables give names to values. Each lesson takes inputs and returns a result; the evaluator checks your work on the server." }
            };
            var mira = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            mira.name = "Mira - Valley Guide NPC";
            mira.transform.position = new Vector3(2f, 1f, 1f);
            mira.GetComponent<Renderer>().material.color = new Color(.2f, .67f, .83f);
            mira.AddComponent<NpcDialogueInteractable>().Initialize(dialogue);
            CreateWorldLabel(mira.transform, "MIRA • VALLEY GUIDE", new Vector3(0f, 1.3f, 0f));

            var portal = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            portal.name = "Variable Valley Learning Gate";
            portal.transform.position = new Vector3(2f, .9f, 10f);
            portal.transform.localScale = new Vector3(1.5f, 2f, .45f);
            portal.GetComponent<Renderer>().material.color = new Color(.25f, .8f, .65f);
            portal.AddComponent<LearningRegionPortalInteractable>().Configure("variable-valley", "Enter Variable Valley");
            CreateWorldLabel(portal.transform, "VARIABLE VALLEY", new Vector3(0f, 1.5f, 0f));

            CreateValleyDecoration("Valley Path", PrimitiveType.Cube, new Vector3(2f, .04f, 5.3f), new Vector3(1.2f, .08f, 10f), new Color(.45f, .34f, .2f));
            CreateValleyDecoration("Valley Gate Left", PrimitiveType.Cube, new Vector3(.8f, 1.5f, 10f), new Vector3(.25f, 3f, .35f), new Color(.13f, .36f, .34f));
            CreateValleyDecoration("Valley Gate Right", PrimitiveType.Cube, new Vector3(3.2f, 1.5f, 10f), new Vector3(.25f, 3f, .35f), new Color(.13f, .36f, .34f));
            CreateValleyDecoration("Valley Gate Header", PrimitiveType.Cube, new Vector3(2f, 3f, 10f), new Vector3(2.7f, .25f, .35f), new Color(.13f, .36f, .34f));
            CreateValleyDecoration("Beacon Plinth", PrimitiveType.Cylinder, new Vector3(2f, .3f, 14f), new Vector3(1.8f, .3f, 1.8f), new Color(.32f, .43f, .28f));
            var beacon = CreateValleyDecoration("Valley Beacon", PrimitiveType.Capsule, new Vector3(2f, 1.6f, 14f), new Vector3(.5f, 1.3f, .5f), new Color(.94f, .72f, .21f));
            CreateWorldLabel(beacon.transform, "BEACON", new Vector3(0f, 1.3f, 0f));
        }

        private static GameObject CreateValleyDecoration(string name, PrimitiveType type, Vector3 position, Vector3 scale, Color color)
        {
            var piece = GameObject.CreatePrimitive(type);
            piece.name = name;
            piece.transform.position = position;
            piece.transform.localScale = scale;
            piece.GetComponent<Renderer>().material.color = color;
            return piece;
        }

        private static void CreateWorldLabel(Transform parent, string label, Vector3 localPosition)
        {
            var labelObject = new GameObject(label + " label");
            labelObject.transform.SetParent(parent, false);
            labelObject.transform.localPosition = localPosition;
            labelObject.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            var mesh = labelObject.AddComponent<TextMesh>();
            mesh.text = label;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.characterSize = .08f;
            mesh.fontSize = 48;
            mesh.color = Color.white;
        }

        private ThirdPersonMotor CreatePlayerAndCamera(out ThirdPersonCameraRig cameraRig)
        {
            if (GameObject.Find("Greybox Ground") == null)
            {
                var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
                floor.name = "Greybox Ground";
                floor.transform.localScale = new Vector3(4f, 1f, 4f);
                floor.GetComponent<Renderer>().material.color = new Color(.23f, .39f, .28f);
            }
            if (FindObjectOfType<Light>() == null)
            {
                var sun = new GameObject("Valley Sun", typeof(Light));
                sun.transform.rotation = Quaternion.Euler(48f, -32f, 0f);
                sun.GetComponent<Light>().type = LightType.Directional;
                sun.GetComponent<Light>().intensity = 1.25f;
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
