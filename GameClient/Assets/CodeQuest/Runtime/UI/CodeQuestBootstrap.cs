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
        private IDisposable _authentication;

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
            IAccessTokenProvider tokens = new UnauthenticatedTokenProvider();
            IInteractiveAuthenticationProvider interactiveAuthentication = null;
#if UNITY_EDITOR_WIN || UNITY_STANDALONE_WIN
            var windowsAuthentication = new WindowsKeycloakTokenProvider();
            tokens = windowsAuthentication;
            interactiveAuthentication = windowsAuthentication;
            _authentication = windowsAuthentication;
#endif
            var api = new CodeQuestApiClient(apiSettings, tokens);
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
            _hud = new RuntimeHud(api, _gameState, interactor, quests, transform, interactiveAuthentication);
            _gameState.ChangeTo(GameState.MainMenu);
        }

        private void OnDestroy()
        {
            _hud?.Dispose();
            _authentication?.Dispose();
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
            var npcCol = npc.GetComponent<CapsuleCollider>();
            if (npcCol != null) { npcCol.center = Vector3.zero; npcCol.height = 2f; npcCol.radius = 0.5f; }
            var npcRend = npc.GetComponent<MeshRenderer>();
            if (npcRend != null) Destroy(npcRend);
            var npcFilter = npc.GetComponent<MeshFilter>();
            if (npcFilter != null) Destroy(npcFilter);
            BuildStylizedNpcVisual(npc.transform, NpcArchetype.SignalKeeper);
            npc.AddComponent<NpcDialogueInteractable>().Initialize(dialogue);
            CreateWorldLabel(npc.transform, "SIGNAL KEEPER", new Vector3(0f, 1.35f, 0f), 0.034f);
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
            var miraCol = mira.GetComponent<CapsuleCollider>();
            if (miraCol != null) { miraCol.center = Vector3.zero; miraCol.height = 2f; miraCol.radius = 0.5f; }
            var miraRend = mira.GetComponent<MeshRenderer>();
            if (miraRend != null) Destroy(miraRend);
            var miraFilter = mira.GetComponent<MeshFilter>();
            if (miraFilter != null) Destroy(miraFilter);
            BuildStylizedNpcVisual(mira.transform, NpcArchetype.MiraGuide);
            mira.AddComponent<NpcDialogueInteractable>().Initialize(dialogue);
            CreateWorldLabel(mira.transform, "MIRA • VALLEY GUIDE", new Vector3(0f, 1.35f, 0f), 0.034f);

            // Preserved core portal trigger & visual object
            var portal = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            portal.name = "Variable Valley Learning Gate";
            portal.transform.position = new Vector3(2f, 1.35f, 10f);
            portal.transform.localScale = new Vector3(1.35f, 2.1f, 0.4f);
            ApplyEmissiveMaterial(portal, new Color(0.12f, 0.82f, 0.72f), 0.05f, 0.95f, new Color(0.10f, 0.75f, 0.65f), 1.8f);
            portal.AddComponent<LearningRegionPortalInteractable>().Configure("variable-valley", "Enter Variable Valley");

            // Cobblestone path leading to the gate
            var path = CreateValleyDecoration("Valley Path", PrimitiveType.Cube, new Vector3(2f, .03f, 5.3f), new Vector3(1.4f, .06f, 10f), new Color(0.48f, 0.44f, 0.38f));
            ApplyTexturedMaterial(path, new Color(0.48f, 0.44f, 0.38f), 0.05f, 0.35f, 6.0f, 40.0f, PatternKind.PavingStone);

            // Architectural Stone Gateway Framing (layered plinths, pillars, capitals, arch lintel)
            // Pillar Plinths (Lower Stone Bases)
            CreateValleyArchPiece("Gate Base Left", PrimitiveType.Cube, new Vector3(0.8f, 0.25f, 10f), new Vector3(0.55f, 0.5f, 0.55f), new Color(0.32f, 0.35f, 0.34f));
            CreateValleyArchPiece("Gate Base Right", PrimitiveType.Cube, new Vector3(3.2f, 0.25f, 10f), new Vector3(0.55f, 0.5f, 0.55f), new Color(0.32f, 0.35f, 0.34f));

            // Main Carved Stone Pillars
            var gateLeft = CreateValleyDecoration("Valley Gate Left", PrimitiveType.Cube, new Vector3(.8f, 1.6f, 10f), new Vector3(.38f, 2.4f, .38f), new Color(0.38f, 0.42f, 0.40f));
            var gateRight = CreateValleyDecoration("Valley Gate Right", PrimitiveType.Cube, new Vector3(3.2f, 1.6f, 10f), new Vector3(.38f, 2.4f, .38f), new Color(0.38f, 0.42f, 0.40f));
            ApplyTexturedMaterial(gateLeft, new Color(0.38f, 0.42f, 0.40f), 0.08f, 0.4f, 2.0f, 8.0f, PatternKind.PavingStone);
            ApplyTexturedMaterial(gateRight, new Color(0.38f, 0.42f, 0.40f), 0.08f, 0.4f, 2.0f, 8.0f, PatternKind.PavingStone);

            // Pillar Capitals
            CreateValleyArchPiece("Gate Capital Left", PrimitiveType.Cube, new Vector3(0.8f, 2.85f, 10f), new Vector3(0.5f, 0.2f, 0.5f), new Color(0.35f, 0.39f, 0.37f));
            CreateValleyArchPiece("Gate Capital Right", PrimitiveType.Cube, new Vector3(3.2f, 2.85f, 10f), new Vector3(0.5f, 0.2f, 0.5f), new Color(0.35f, 0.39f, 0.37f));

            // Top Header & Keystone Arch
            var gateHeader = CreateValleyDecoration("Valley Gate Header", PrimitiveType.Cube, new Vector3(2f, 3.05f, 10f), new Vector3(2.9f, .3f, .42f), new Color(0.36f, 0.40f, 0.38f));
            ApplyTexturedMaterial(gateHeader, new Color(0.36f, 0.40f, 0.38f), 0.08f, 0.4f, 8.0f, 1.5f, PatternKind.PavingStone);
            var keystone = CreateValleyArchPiece("Gate Keystone", PrimitiveType.Cube, new Vector3(2f, 3.25f, 10f), new Vector3(0.48f, 0.32f, 0.48f), new Color(0.42f, 0.46f, 0.44f));
            ApplyStylizedMaterial(keystone, new Color(0.42f, 0.46f, 0.44f), 0.1f, 0.5f);

            // Distinct Gateway Label positioned clearly above the stone arch lintel (not intersecting the portal sphere)
            CreateWorldLabel(gateHeader.transform, "VARIABLE VALLEY", new Vector3(0f, 0.55f, 0f), 0.038f);

            // Ancient Beacon Monument with Stepped Stone Base & Metallic Rune Rings
            CreateValleyArchPiece("Beacon Lower Plinth", PrimitiveType.Cylinder, new Vector3(2f, .15f, 14f), new Vector3(2.4f, .15f, 2.4f), new Color(0.34f, 0.37f, 0.35f));
            var plinth = CreateValleyDecoration("Beacon Plinth", PrimitiveType.Cylinder, new Vector3(2f, .4f, 14f), new Vector3(1.7f, .25f, 1.7f), new Color(0.38f, 0.41f, 0.39f));
            ApplyTexturedMaterial(plinth, new Color(0.38f, 0.41f, 0.39f), 0.08f, 0.45f, 4f, 4f, PatternKind.PavingStone);

            // Beacon Pedestal & Glowing Core
            CreateValleyArchPiece("Beacon Pedestal", PrimitiveType.Cylinder, new Vector3(2f, .75f, 14f), new Vector3(0.9f, .35f, 0.9f), new Color(0.28f, 0.30f, 0.29f));
            var beacon = CreateValleyDecoration("Valley Beacon", PrimitiveType.Capsule, new Vector3(2f, 1.6f, 14f), new Vector3(.5f, 1.2f, .5f), new Color(0.96f, 0.78f, 0.24f));
            ApplyEmissiveMaterial(beacon, new Color(0.96f, 0.78f, 0.24f), 0.35f, 0.88f, new Color(0.95f, 0.68f, 0.12f), 2.2f);
            var beaconCollider = beacon.GetComponent<Collider>();
            if (beaconCollider == null) beaconCollider = beacon.AddComponent<CapsuleCollider>();
            beaconCollider.isTrigger = false;
            beacon.AddComponent<ChallengeBeaconInteractable>().Configure("valley-name-tag", "Inspect Valley Beacon / Open Python Challenge");
            // Bronze Focus Ring
            CreateValleyArchPiece("Beacon Bronze Ring", PrimitiveType.Cylinder, new Vector3(2f, 1.6f, 14f), new Vector3(0.72f, 0.08f, 0.72f), new Color(0.72f, 0.52f, 0.22f));
            CreateWorldLabel(beacon.transform, "VALLEY BEACON", new Vector3(0f, 1.15f, 0f), 0.028f);

            // Atmospheric point light near the beacon
            var beaconLightObj = new GameObject("Beacon Warm Light", typeof(Light));
            beaconLightObj.transform.position = new Vector3(2f, 2.2f, 14f);
            var bLight = beaconLightObj.GetComponent<Light>();
            bLight.type = LightType.Point;
            bLight.range = 7.5f;
            bLight.intensity = 1.9f;
            bLight.color = new Color(1.0f, 0.88f, 0.65f);

            // Subtle portal glow
            var portalLightObj = new GameObject("Portal Ethereal Light", typeof(Light));
            portalLightObj.transform.position = new Vector3(2f, 1.35f, 10f);
            var pLight = portalLightObj.GetComponent<Light>();
            pLight.type = LightType.Point;
            pLight.range = 5.5f;
            pLight.intensity = 1.6f;
            pLight.color = new Color(0.35f, 0.95f, 0.85f);

            // Decorative natural scenery outside walkable areas
            CreateDistantScenery();
        }

        private static GameObject CreateValleyArchPiece(string name, PrimitiveType type, Vector3 position, Vector3 scale, Color color)
        {
            var piece = GameObject.CreatePrimitive(type);
            piece.name = name;
            piece.transform.position = position;
            piece.transform.localScale = scale;
            ApplyStylizedMaterial(piece, color, 0.06f, 0.38f);
            return piece;
        }

        private static void CreateDistantScenery()
        {
            var decorRoot = new GameObject("Valley Environment Scenery");

            // Distant soft hillside mounds far beyond the playable zone (gentle horizon, not boxy cubes)
            CreateHill(decorRoot.transform, new Vector3(-18f, -0.5f, 14f), new Vector3(14f, 4.5f, 12f), new Color(0.36f, 0.52f, 0.34f));
            CreateHill(decorRoot.transform, new Vector3(-16f, -0.2f, 26f), new Vector3(16f, 6.0f, 14f), new Color(0.34f, 0.48f, 0.32f));
            CreateHill(decorRoot.transform, new Vector3(20f, -0.5f, 16f), new Vector3(15f, 5.0f, 13f), new Color(0.36f, 0.52f, 0.34f));
            CreateHill(decorRoot.transform, new Vector3(18f, -0.8f, 6f), new Vector3(12f, 3.8f, 10f), new Color(0.38f, 0.54f, 0.36f));
            CreateHill(decorRoot.transform, new Vector3(2f, -0.2f, 30f), new Vector3(22f, 7.0f, 15f), new Color(0.32f, 0.46f, 0.30f));

            // Roadside natural rounded riverbed stones (scaled down, non-blocking)
            CreatePebble(decorRoot.transform, new Vector3(0.5f, 0.12f, 3.5f), new Vector3(0.45f, 0.22f, 0.4f), new Color(0.58f, 0.56f, 0.52f));
            CreatePebble(decorRoot.transform, new Vector3(3.5f, 0.15f, 6.2f), new Vector3(0.55f, 0.28f, 0.5f), new Color(0.55f, 0.53f, 0.50f));
            CreatePebble(decorRoot.transform, new Vector3(0.6f, 0.14f, 8.5f), new Vector3(0.48f, 0.25f, 0.42f), new Color(0.56f, 0.54f, 0.51f));
            CreatePebble(decorRoot.transform, new Vector3(3.6f, 0.18f, 12.5f), new Vector3(0.65f, 0.32f, 0.55f), new Color(0.54f, 0.52f, 0.49f));

            // Natural vibrant valley foliage clusters (shrubs away from the walking corridor)
            CreateShrub(decorRoot.transform, new Vector3(-0.4f, 0.28f, 2.0f), 0.55f, new Color(0.26f, 0.55f, 0.28f));
            CreateShrub(decorRoot.transform, new Vector3(4.3f, 0.35f, 4.0f), 0.65f, new Color(0.30f, 0.58f, 0.32f));
            CreateShrub(decorRoot.transform, new Vector3(-0.3f, 0.32f, 6.5f), 0.6f, new Color(0.28f, 0.54f, 0.30f));
            CreateShrub(decorRoot.transform, new Vector3(4.4f, 0.38f, 9.0f), 0.7f, new Color(0.25f, 0.52f, 0.28f));
            CreateShrub(decorRoot.transform, new Vector3(4.2f, 0.42f, 13.5f), 0.75f, new Color(0.32f, 0.60f, 0.34f));
        }

        private static void CreateHill(Transform parent, Vector3 position, Vector3 scale, Color color)
        {
            var hill = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            hill.name = "Valley Hill";
            hill.transform.SetParent(parent, false);
            hill.transform.position = position;
            hill.transform.localScale = scale;
            var col = hill.GetComponent<Collider>();
            if (col != null) Destroy(col);
            ApplyStylizedMaterial(hill, color, 0.02f, 0.15f);
        }

        private static void CreatePebble(Transform parent, Vector3 position, Vector3 scale, Color color)
        {
            var pebble = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            pebble.name = "Valley Stone";
            pebble.transform.SetParent(parent, false);
            pebble.transform.position = position;
            pebble.transform.localScale = scale;
            var col = pebble.GetComponent<Collider>();
            if (col != null) Destroy(col);
            ApplyStylizedMaterial(pebble, color, 0.05f, 0.35f);
        }

        private static void CreateShrub(Transform parent, Vector3 position, float scale, Color color)
        {
            var bush = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            bush.name = "Valley Shrub";
            bush.transform.SetParent(parent, false);
            bush.transform.position = position;
            bush.transform.localScale = new Vector3(scale * 1.25f, scale * 0.85f, scale * 1.15f);
            var col = bush.GetComponent<Collider>();
            if (col != null) Destroy(col);
            ApplyStylizedMaterial(bush, color, 0.0f, 0.2f);
        }

        private static GameObject CreateValleyDecoration(string name, PrimitiveType type, Vector3 position, Vector3 scale, Color color)
        {
            var piece = GameObject.CreatePrimitive(type);
            piece.name = name;
            piece.transform.position = position;
            piece.transform.localScale = scale;
            ApplyStylizedMaterial(piece, color, 0.05f, 0.35f);
            return piece;
        }

        private enum PatternKind { MeadowGrass, PavingStone }
        private static Texture2D _grassTexture;
        private static Texture2D _stoneTexture;

        private static Texture2D GetProceduralTexture(PatternKind kind)
        {
            if (kind == PatternKind.MeadowGrass)
            {
                if (_grassTexture != null) return _grassTexture;
                _grassTexture = GenerateNoiseTexture(128, new Color(0.38f, 0.58f, 0.32f), new Color(0.44f, 0.65f, 0.36f), 0.18f);
                return _grassTexture;
            }
            if (_stoneTexture != null) return _stoneTexture;
            _stoneTexture = GenerateNoiseTexture(128, new Color(0.48f, 0.44f, 0.38f), new Color(0.55f, 0.51f, 0.45f), 0.22f);
            return _stoneTexture;
        }

        private static Texture2D GenerateNoiseTexture(int size, Color baseCol, Color varCol, float noiseWeight)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, true);
            tex.wrapMode = TextureWrapMode.Repeat;
            tex.filterMode = FilterMode.Bilinear;
            var pixels = new Color[size * size];
            for (var y = 0; y < size; y++)
            {
                for (var x = 0; x < size; x++)
                {
                    var n1 = Mathf.PerlinNoise(x * 0.15f, y * 0.15f);
                    var n2 = Mathf.PerlinNoise(x * 0.45f + 17f, y * 0.45f + 31f) * 0.5f;
                    var t = Mathf.Clamp01((n1 + n2) * 0.75f);
                    pixels[y * size + x] = Color.Lerp(baseCol, varCol, t);
                }
            }
            tex.SetPixels(pixels);
            tex.Apply(true, true);
            return tex;
        }

        private static void ApplyTexturedMaterial(GameObject target, Color albedo, float metallic, float smoothness, float tileX, float tileY, PatternKind pattern)
        {
            var renderer = target.GetComponent<Renderer>();
            if (renderer == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            var mat = shader != null ? new Material(shader) : renderer.material;
            var tex = GetProceduralTexture(pattern);
            if (tex != null)
            {
                if (mat.HasProperty("_BaseMap"))
                {
                    mat.SetTexture("_BaseMap", tex);
                    mat.SetTextureScale("_BaseMap", new Vector2(tileX, tileY));
                }
                else if (mat.HasProperty("_MainTex"))
                {
                    mat.SetTexture("_MainTex", tex);
                    mat.SetTextureScale("_MainTex", new Vector2(tileX, tileY));
                }
            }
            mat.color = albedo;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", albedo);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            renderer.material = mat;
        }

        private static void ApplyStylizedMaterial(GameObject target, Color albedo, float metallic, float smoothness)
        {
            var renderer = target.GetComponent<Renderer>();
            if (renderer == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            var mat = shader != null ? new Material(shader) : renderer.material;
            mat.color = albedo;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", albedo);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            renderer.material = mat;
        }

        private static void ApplyEmissiveMaterial(GameObject target, Color albedo, float metallic, float smoothness, Color emissionColor, float emissionIntensity)
        {
            var renderer = target.GetComponent<Renderer>();
            if (renderer == null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            var mat = shader != null ? new Material(shader) : renderer.material;
            mat.color = albedo;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", albedo);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_EmissionColor"))
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", emissionColor * emissionIntensity);
            }
            renderer.material = mat;
        }

        private static void CreateWorldLabel(Transform parent, string label, Vector3 localPosition, float charSize = 0.035f)
        {
            var labelObject = new GameObject(label + " label");
            labelObject.transform.SetParent(parent, false);
            labelObject.transform.localPosition = localPosition;
            // Face the default camera angle without mirror inversion (Y=0, normal front view)
            labelObject.transform.localRotation = Quaternion.identity;
            labelObject.AddComponent<WorldBillboardLabel>();
            var mesh = labelObject.AddComponent<TextMesh>();
            mesh.text = label;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.characterSize = charSize;
            mesh.fontSize = 44;
            mesh.color = Color.white;
        }

        private sealed class WorldBillboardLabel : MonoBehaviour
        {
            private void LateUpdate()
            {
                var cam = Camera.main;
                if (cam == null) return;
                // Face the camera directly so text always reads correctly left-to-right from any angle
                transform.rotation = cam.transform.rotation;
            }
        }

        private ThirdPersonMotor CreatePlayerAndCamera(out ThirdPersonCameraRig cameraRig)
        {
            if (GameObject.Find("Greybox Ground") == null)
            {
                var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
                floor.name = "Greybox Ground";
                floor.transform.localScale = new Vector3(6f, 1f, 6f);
                // Fresh, vibrant daylight meadow grass with natural procedural micro-detail
                ApplyTexturedMaterial(floor, new Color(0.38f, 0.58f, 0.32f), 0.02f, 0.18f, 24.0f, 24.0f, PatternKind.MeadowGrass);
            }
            if (FindObjectOfType<Light>() == null)
            {
                var sun = new GameObject("Valley Sun", typeof(Light));
                sun.transform.rotation = Quaternion.Euler(52f, -38f, 0f);
                var lightComp = sun.GetComponent<Light>();
                lightComp.type = LightType.Directional;
                lightComp.color = new Color(1.0f, 0.97f, 0.90f); // Bright clean sun
                lightComp.intensity = 1.45f;
                lightComp.shadows = LightShadows.Soft;
                lightComp.shadowStrength = 0.65f; // Softer, clearer shadows preserving ground detail
            }

            // Fresh sunny daylight atmosphere & blue sky horizon
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(0.72f, 0.84f, 0.94f); // Crisp sky blue horizon
            RenderSettings.fogStartDistance = 25f; // Push fog back so nearby valley is bright and clear
            RenderSettings.fogEndDistance = 95f;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.65f, 0.75f, 0.88f); // Bright sky ambient
            RenderSettings.ambientEquatorColor = new Color(0.50f, 0.58f, 0.52f); // Lighter equator bounce
            RenderSettings.ambientGroundColor = new Color(0.32f, 0.42f, 0.30f); // Bright grass bounce

            var playerObject = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            playerObject.name = "Player";
            playerObject.transform.position = new Vector3(0f, 1f, 0f);
            var visualCollider = playerObject.GetComponent<CapsuleCollider>();
            if (visualCollider != null) Destroy(visualCollider);
            var playerRend = playerObject.GetComponent<MeshRenderer>();
            if (playerRend != null) Destroy(playerRend);
            var playerFilter = playerObject.GetComponent<MeshFilter>();
            if (playerFilter != null) Destroy(playerFilter);

            var controller = playerObject.AddComponent<CharacterController>();
            controller.center = Vector3.zero;
            controller.height = 2f;
            controller.radius = 0.5f;

            var motor = playerObject.AddComponent<ThirdPersonMotor>();
            playerObject.AddComponent<PlayerInteractor>();
            AttachPlayerVisual(playerObject.transform, motor);

            cameraRig = CreateCamera(playerObject.transform);
            cameraRig.Configure(new Vector3(0f, 1.4f, 0f), 4.2f, 2.2f);
            return motor;
        }

        private static void AttachPlayerVisual(Transform playerRoot, ThirdPersonMotor motor)
        {
            var config = Resources.Load<KenneyCharacterVisualConfig>("Kenney/KenneyCharacterVisualConfig");
#if UNITY_EDITOR
            if (config == null)
            {
                config = UnityEditor.AssetDatabase.LoadAssetAtPath<KenneyCharacterVisualConfig>(
                    "Assets/Resources/Kenney/KenneyCharacterVisualConfig.asset");
            }
#endif
            if (config != null && config.characterModel != null)
            {
                var visual = Instantiate(config.characterModel, playerRoot);
                visual.name = "PlayerKenneyVisual";
                // CharacterController height is 2f centered at Vector3.zero.
                // An offset of -0.88f aligns the Kenney character's feet with the ground/path contact surface,
                // preventing the lower legs from sinking below the ground plane during idle/standing.
                visual.transform.localPosition = new Vector3(0f, -0.88f, 0f);
                visual.transform.localRotation = Quaternion.identity;
                visual.transform.localScale = Vector3.one;

                // Remove any colliders that could interfere with CharacterController
                var colliders = visual.GetComponentsInChildren<Collider>(true);
                foreach (var col in colliders)
                {
                    Destroy(col);
                }

                // Apply verified HumanMaleA material and configure robust skinning/bounds
                var skinnedRenderer = visual.GetComponentInChildren<SkinnedMeshRenderer>();
                if (skinnedRenderer != null)
                {
                    if (config.humanMaleMaterial != null)
                    {
                        skinnedRenderer.sharedMaterial = config.humanMaleMaterial;
                    }

                    // Preserve the Kenney prefab's authored rootBone (HipsCtrl) so lower limb
                    // skinning matrices bind correctly; only fallback if rootBone was null.
                    if (skinnedRenderer.rootBone == null)
                    {
                        var rootBone = visual.transform.Find("Root/HipsCtrl") ?? visual.transform.Find("Root");
                        if (rootBone != null) skinnedRenderer.rootBone = rootBone;
                    }
                    skinnedRenderer.updateWhenOffscreen = true;
                    skinnedRenderer.localBounds = new Bounds(new Vector3(0f, 0.9f, 0f), new Vector3(2f, 2.2f, 2f));
                }

                // Configure Animator with Humanoid Avatar and Animator Controller
                var animator = visual.GetComponent<Animator>();
                if (animator == null) animator = visual.AddComponent<Animator>();
                if (config.characterAvatar != null) animator.avatar = config.characterAvatar;
                if (config.animatorController != null) animator.runtimeAnimatorController = config.animatorController;
                animator.applyRootMotion = false;

                if (motor != null)
                {
                    motor.BindAnimator(animator);
                }

                return;
            }

            // Fallback to stylized procedural visual if config not found
            BuildStylizedPlayerVisual(playerRoot);
        }

        private enum NpcArchetype { MiraGuide, SignalKeeper }

        private static void BuildStylizedPlayerVisual(Transform playerRoot)
        {
            var rig = new GameObject("PlayerVisualRig");
            rig.transform.SetParent(playerRoot, false);
            rig.transform.localPosition = Vector3.zero;
            rig.transform.localRotation = Quaternion.identity;

            // Torso / Tunic
            var tunicCol = new Color(0.22f, 0.44f, 0.72f); // Explorer Cobalt Blue
            var beltCol = new Color(0.28f, 0.20f, 0.14f);  // Leather Brown
            var skinCol = new Color(0.92f, 0.76f, 0.62f);  // Warm Skin Tone
            var hairCol = new Color(0.18f, 0.14f, 0.12f);  // Dark Chestnut
            var bootCol = new Color(0.20f, 0.16f, 0.12f);  // Sturdy Boots
            var pantCol = new Color(0.24f, 0.26f, 0.30f);  // Slate Trousers

            var torso = CreateRigPart("Torso", PrimitiveType.Cube, rig.transform, new Vector3(0f, 0.05f, 0f), new Vector3(0.55f, 0.65f, 0.32f), tunicCol);
            var belt = CreateRigPart("Belt", PrimitiveType.Cube, torso.transform, new Vector3(0f, -0.24f, 0f), new Vector3(1.04f, 0.16f, 1.04f), beltCol);
            var buckle = CreateRigPart("Buckle", PrimitiveType.Cube, belt.transform, new Vector3(0f, 0f, 0.52f), new Vector3(0.28f, 0.8f, 0.15f), new Color(0.85f, 0.72f, 0.28f));

            // Head & Hair
            var head = CreateRigPart("Head", PrimitiveType.Sphere, rig.transform, new Vector3(0f, 0.62f, 0f), new Vector3(0.42f, 0.44f, 0.42f), skinCol);
            var hair = CreateRigPart("Hair", PrimitiveType.Cube, head.transform, new Vector3(0f, 0.14f, -0.05f), new Vector3(1.05f, 0.65f, 1.1f), hairCol);
            // Explorer Visor / Hair fringe
            CreateRigPart("Fringe", PrimitiveType.Cube, head.transform, new Vector3(0f, 0.22f, 0.15f), new Vector3(0.95f, 0.35f, 0.65f), hairCol);

            // Left & Right Arms
            var leftArm = CreateRigPart("LeftArm", PrimitiveType.Capsule, rig.transform, new Vector3(-0.38f, 0.05f, 0f), new Vector3(0.18f, 0.55f, 0.18f), tunicCol);
            var rightArm = CreateRigPart("RightArm", PrimitiveType.Capsule, rig.transform, new Vector3(0.38f, 0.05f, 0f), new Vector3(0.18f, 0.55f, 0.18f), tunicCol);
            CreateRigPart("LeftHand", PrimitiveType.Sphere, leftArm.transform, new Vector3(0f, -0.35f, 0f), new Vector3(1.1f, 0.35f, 1.1f), skinCol);
            CreateRigPart("RightHand", PrimitiveType.Sphere, rightArm.transform, new Vector3(0f, -0.35f, 0f), new Vector3(1.1f, 0.35f, 1.1f), skinCol);

            // Left & Right Legs & Boots
            var leftLeg = CreateRigPart("LeftLeg", PrimitiveType.Capsule, rig.transform, new Vector3(-0.16f, -0.58f, 0f), new Vector3(0.20f, 0.58f, 0.20f), pantCol);
            var rightLeg = CreateRigPart("RightLeg", PrimitiveType.Capsule, rig.transform, new Vector3(0.16f, -0.58f, 0f), new Vector3(0.20f, 0.58f, 0.20f), pantCol);
            CreateRigPart("LeftBoot", PrimitiveType.Cube, leftLeg.transform, new Vector3(0f, -0.36f, 0.08f), new Vector3(1.15f, 0.32f, 1.45f), bootCol);
            CreateRigPart("RightBoot", PrimitiveType.Cube, rightLeg.transform, new Vector3(0f, -0.36f, 0.08f), new Vector3(1.15f, 0.32f, 1.45f), bootCol);

            // Procedural natural locomotion animator
            var anim = rig.AddComponent<ProceduralWalkAnimator>();
            anim.Initialize(leftArm.transform, rightArm.transform, leftLeg.transform, rightLeg.transform, head.transform, true);
        }

        private static void BuildStylizedNpcVisual(Transform npcRoot, NpcArchetype archetype)
        {
            var rig = new GameObject("NpcVisualRig");
            rig.transform.SetParent(npcRoot, false);
            rig.transform.localPosition = Vector3.zero;
            rig.transform.localRotation = Quaternion.identity;

            Color robeCol, cloakCol, skinCol, hairCol;
            if (archetype == NpcArchetype.MiraGuide)
            {
                robeCol = new Color(0.16f, 0.48f, 0.68f);   // Cerulean Scholar Robe
                cloakCol = new Color(0.22f, 0.62f, 0.54f);  // Valley Emerald Mantle
                skinCol = new Color(0.94f, 0.78f, 0.65f);   // Warm Skin Tone
                hairCol = new Color(0.58f, 0.34f, 0.18f);   // Auburn Hair
            }
            else
            {
                robeCol = new Color(0.38f, 0.34f, 0.44f);   // Twilight Keeper Robe
                cloakCol = new Color(0.68f, 0.48f, 0.22f);  // Bronze Beacon Scarf
                skinCol = new Color(0.88f, 0.74f, 0.62f);
                hairCol = new Color(0.72f, 0.72f, 0.76f);   // Silver Elder Hair
            }

            // Robe / Body
            var torso = CreateRigPart("Torso", PrimitiveType.Cube, rig.transform, new Vector3(0f, 0.0f, 0f), new Vector3(0.58f, 0.72f, 0.36f), robeCol);
            var skirt = CreateRigPart("RobeSkirt", PrimitiveType.Cylinder, rig.transform, new Vector3(0f, -0.52f, 0f), new Vector3(0.54f, 0.42f, 0.50f), robeCol);

            // Cloak / Mantle Shoulders
            CreateRigPart("Mantle", PrimitiveType.Cube, torso.transform, new Vector3(0f, 0.28f, 0f), new Vector3(1.18f, 0.22f, 1.25f), cloakCol);
            CreateRigPart("CapeBack", PrimitiveType.Cube, torso.transform, new Vector3(0f, -0.15f, -0.22f), new Vector3(0.92f, 0.85f, 0.12f), cloakCol);

            // Head & Hair/Headdress
            var head = CreateRigPart("Head", PrimitiveType.Sphere, rig.transform, new Vector3(0f, 0.64f, 0f), new Vector3(0.44f, 0.46f, 0.44f), skinCol);
            var hair = CreateRigPart("Hair", PrimitiveType.Sphere, head.transform, new Vector3(0f, 0.12f, -0.08f), new Vector3(1.08f, 0.85f, 1.12f), hairCol);
            if (archetype == NpcArchetype.MiraGuide)
            {
                // Guide diadem circlet
                CreateRigPart("Circlet", PrimitiveType.Cylinder, head.transform, new Vector3(0f, 0.18f, 0.04f), new Vector3(1.06f, 0.06f, 1.06f), new Color(0.92f, 0.82f, 0.35f));
            }

            // Arms & Sleeves
            var leftArm = CreateRigPart("LeftArm", PrimitiveType.Capsule, rig.transform, new Vector3(-0.40f, 0.04f, 0f), new Vector3(0.20f, 0.55f, 0.20f), robeCol);
            var rightArm = CreateRigPart("RightArm", PrimitiveType.Capsule, rig.transform, new Vector3(0.40f, 0.04f, 0f), new Vector3(0.20f, 0.55f, 0.20f), robeCol);
            CreateRigPart("LeftHand", PrimitiveType.Sphere, leftArm.transform, new Vector3(0f, -0.34f, 0f), new Vector3(1.1f, 0.35f, 1.1f), skinCol);
            CreateRigPart("RightHand", PrimitiveType.Sphere, rightArm.transform, new Vector3(0f, -0.34f, 0f), new Vector3(1.1f, 0.35f, 1.1f), skinCol);

            // Idle breathing and greeting animator
            var anim = rig.AddComponent<ProceduralWalkAnimator>();
            anim.Initialize(leftArm.transform, rightArm.transform, null, null, head.transform, false);
        }

        private static GameObject CreateRigPart(string name, PrimitiveType type, Transform parent, Vector3 localPos, Vector3 localScale, Color color)
        {
            var part = GameObject.CreatePrimitive(type);
            part.name = name;
            var col = part.GetComponent<Collider>();
            if (col != null) Destroy(col);
            part.transform.SetParent(parent, false);
            part.transform.localPosition = localPos;
            part.transform.localScale = localScale;
            part.transform.localRotation = Quaternion.identity;
            ApplyStylizedMaterial(part, color, 0.08f, 0.42f);
            return part;
        }

        private sealed class ProceduralWalkAnimator : MonoBehaviour
        {
            private Transform _leftArm;
            private Transform _rightArm;
            private Transform _leftLeg;
            private Transform _rightLeg;
            private Transform _head;
            private bool _isPlayer;
            private CharacterController _characterController;
            private Vector3 _lastPosition;
            private float _walkCycle;

            public void Initialize(Transform leftArm, Transform rightArm, Transform leftLeg, Transform rightLeg, Transform head, bool isPlayer)
            {
                _leftArm = leftArm;
                _rightArm = rightArm;
                _leftLeg = leftLeg;
                _rightLeg = rightLeg;
                _head = head;
                _isPlayer = isPlayer;
                _characterController = GetComponentInParent<CharacterController>();
                _lastPosition = transform.position;
            }

            private void Update()
            {
                var dt = Time.deltaTime;
                if (dt <= 0.00001f) return;

                if (_isPlayer && _characterController != null)
                {
                    var velocity = (transform.position - _lastPosition) / dt;
                    _lastPosition = transform.position;
                    var horizontalSpeed = new Vector2(velocity.x, velocity.z).magnitude;
                    var isMoving = horizontalSpeed > 0.15f;

                    if (isMoving)
                    {
                        var cadence = Mathf.Clamp(horizontalSpeed * 2.8f, 3.5f, 9.5f);
                        _walkCycle += dt * cadence;
                        var swing = Mathf.Sin(_walkCycle) * 32f;
                        var counterSwing = -swing;

                        if (_leftLeg != null) _leftLeg.localRotation = Quaternion.Euler(swing, 0f, 0f);
                        if (_rightLeg != null) _rightLeg.localRotation = Quaternion.Euler(counterSwing, 0f, 0f);
                        if (_leftArm != null) _leftArm.localRotation = Quaternion.Euler(counterSwing * 0.85f, 0f, 0f);
                        if (_rightArm != null) _rightArm.localRotation = Quaternion.Euler(swing * 0.85f, 0f, 0f);
                        if (_head != null) _head.localRotation = Quaternion.Euler(Mathf.Sin(_walkCycle * 2f) * 2f, 0f, 0f);
                    }
                    else
                    {
                        // Player Idle Breathing
                        var idleTime = Time.time * 2.2f;
                        var breath = Mathf.Sin(idleTime) * 3.5f;
                        if (_leftLeg != null) _leftLeg.localRotation = Quaternion.Lerp(_leftLeg.localRotation, Quaternion.identity, dt * 8f);
                        if (_rightLeg != null) _rightLeg.localRotation = Quaternion.Lerp(_rightLeg.localRotation, Quaternion.identity, dt * 8f);
                        if (_leftArm != null) _leftArm.localRotation = Quaternion.Euler(breath, 0f, -5f);
                        if (_rightArm != null) _rightArm.localRotation = Quaternion.Euler(breath, 0f, 5f);
                        if (_head != null) _head.localRotation = Quaternion.Euler(Mathf.Sin(idleTime * 0.7f) * 2.5f, 0f, 0f);
                    }
                }
                else
                {
                    // NPC Idle Breathing & Subtle Head Look
                    var npcTime = Time.time * 1.8f;
                    var breath = Mathf.Sin(npcTime) * 4f;
                    if (_leftArm != null) _leftArm.localRotation = Quaternion.Euler(breath, 0f, -4f);
                    if (_rightArm != null) _rightArm.localRotation = Quaternion.Euler(breath, 0f, 4f);
                    if (_head != null)
                    {
                        var headYaw = Mathf.Sin(npcTime * 0.45f) * 6f;
                        var headPitch = Mathf.Cos(npcTime * 0.8f) * 2.5f;
                        _head.localRotation = Quaternion.Euler(headPitch, headYaw, 0f);
                    }
                }
            }
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
    }
}
