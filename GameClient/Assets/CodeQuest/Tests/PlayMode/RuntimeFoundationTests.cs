using System.Collections;
using System;
using System.Reflection;
using System.Threading;
using CodeQuest.Gameplay.Camera;
using CodeQuest.Gameplay.Dialogue;
using CodeQuest.Gameplay.Input;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Gameplay.Player;
using CodeQuest.Networking;
using CodeQuest.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace CodeQuest.Tests.PlayMode
{
    public sealed class RuntimeFoundationTests
    {
        [UnityTest]
        public IEnumerator CharacterMotorMovesRelativeToCameraForward()
        {
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.transform.position = new Vector3(30f, 0f, 0f);
            var player = new GameObject("motor-test-player");
            player.transform.position = new Vector3(30f, 1f, 0f);
            player.AddComponent<CharacterController>();
            var motor = player.AddComponent<ThirdPersonMotor>();
            var orientation = new GameObject("motor-test-camera").transform;
            motor.Initialize(new FixedInput { Move = Vector2.up }, orientation);
            for (var frame = 0; frame < 20; frame++) yield return null;
            Assert.Greater(player.transform.position.z, 0.001f);
            Assert.That(player.transform.position.x, Is.EqualTo(30f).Within(0.01f));
            Object.Destroy(ground);
            Object.Destroy(player);
            Object.Destroy(orientation.gameObject);
        }

        [UnityTest]
        public IEnumerator InteractorInvokesNearbyInterfaceTarget()
        {
            var player = new GameObject("interactor-test-player");
            player.transform.position = new Vector3(50f, 0f, 0f);
            var interactor = player.AddComponent<PlayerInteractor>();
            interactor.Initialize(new FixedInput());
            var target = new GameObject("interactor-test-target");
            target.transform.position = new Vector3(50f, 0f, 1f);
            target.AddComponent<SphereCollider>().isTrigger = true;
            var interactable = target.AddComponent<PlayModeTestInteractable>();
            yield return null;
            var canceled = 0;
            interactor.InteractionCanceled += _ => canceled++;
            Assert.IsTrue(interactor.TryInteract());
            Assert.AreEqual(1, interactable.InteractionCount);
            interactor.CancelCurrentInteraction();
            Assert.AreEqual(1, canceled);
            Object.Destroy(player);
            Object.Destroy(target);
        }

        [UnityTest]
        public IEnumerator InteractorSelectsNearestThenStableIdAndShowsUnavailablePrompt()
        {
            var player = new GameObject("selector-player");
            player.transform.position = new Vector3(70f, 0f, 0f);
            var interactor = player.AddComponent<PlayerInteractor>();
            interactor.Initialize(new FixedInput());
            var farther = MakeTarget("z-target", new Vector3(70f, 0f, 1.5f), true);
            var nearest = MakeTarget("b-target", new Vector3(70f, 0f, 1f), false);
            var tied = MakeTarget("a-target", new Vector3(70f, 0f, -1f), false);
            yield return null;
            Assert.AreSame(tied.GetComponent<PlayModeTestInteractable>(), interactor.CurrentTarget);
            Assert.AreEqual("Unavailable for test", interactor.CurrentPrompt);
            Assert.IsFalse(interactor.TryInteract());
            Object.Destroy(player); Object.Destroy(farther); Object.Destroy(nearest); Object.Destroy(tied);
        }

        private static GameObject MakeTarget(string id, Vector3 position, bool available)
        {
            var target = new GameObject(id);
            target.transform.position = position;
            target.AddComponent<SphereCollider>().isTrigger = true;
            var interactable = target.AddComponent<PlayModeTestInteractable>();
            interactable.Configure(id, available);
            return target;
        }

        [UnityTest]
        public IEnumerator RuntimeBootstrapIsPresentWhenPlayModeStarts()
        {
            yield return null;
            Assert.IsNotNull(Object.FindObjectOfType<CodeQuestBootstrap>());
            Assert.IsNotNull(Object.FindObjectOfType<ThirdPersonMotor>());
            Assert.IsNotNull(Object.FindObjectOfType<ThirdPersonCameraRig>());
            Assert.IsNotNull(Object.FindObjectOfType<PlayerInteractor>());
            Assert.IsNotNull(Object.FindObjectOfType<UnityEngine.EventSystems.EventSystem>());
            Assert.IsNotNull(Object.FindObjectOfType<Canvas>());
            var menu = GameObject.Find("Main Menu");
            Assert.IsNotNull(menu);
            Assert.IsTrue(menu.activeSelf);
            Assert.IsNotNull(Camera.main);
        }

        [UnityTest]
        public IEnumerator RuntimeHubContainsValleyMentorAndLearningPortal()
        {
            yield return null;
            var mentor = GameObject.Find("Mira - Valley Guide NPC");
            var portal = GameObject.Find("Variable Valley Learning Gate");
            Assert.IsNotNull(mentor);
            Assert.IsNotNull(mentor.GetComponent<NpcDialogueInteractable>());
            Assert.IsNotNull(portal);
            Assert.IsNotNull(portal.GetComponent<LearningRegionPortalInteractable>());
            Assert.AreEqual("variable-valley", portal.GetComponent<LearningRegionPortalInteractable>().RegionSlug);
        }

        [UnityTest]
        public IEnumerator LearningPortalPublishesAnInteractionActivation()
        {
            var player = new GameObject("portal-test-player");
            player.transform.position = new Vector3(90f, 0f, 0f);
            var interactor = player.AddComponent<PlayerInteractor>();
            interactor.Initialize(new FixedInput());
            var portalObject = new GameObject("portal-test-target");
            portalObject.transform.position = new Vector3(90f, 0f, 1f);
            portalObject.AddComponent<SphereCollider>().isTrigger = true;
            var portal = portalObject.AddComponent<LearningRegionPortalInteractable>();
            portal.Configure("variable-valley", "Enter Variable Valley");
            var activated = false;
            portal.Activated += () => activated = true;
            yield return null;
            Assert.IsTrue(interactor.TryInteract());
            Assert.IsTrue(activated);
            Object.Destroy(player);
            Object.Destroy(portalObject);
        }

        [UnityTest]
        public IEnumerator ApiClientReadsLiveCatalogAndRejectsUnauthenticatedProfile()
        {
            var baseUrl = Environment.GetEnvironmentVariable("CODEQUEST_TEST_API_BASE_URL");
            if (string.IsNullOrWhiteSpace(baseUrl))
                Assert.Ignore("Set CODEQUEST_TEST_API_BASE_URL to run the live backend integration check.");

            var settings = ScriptableObject.CreateInstance<ApiClientSettings>();
            typeof(ApiClientSettings).GetField("baseUrl", BindingFlags.Instance | BindingFlags.NonPublic)
                .SetValue(settings, baseUrl);
            var api = new CodeQuestApiClient(settings, new UnauthenticatedTokenProvider());

            var catalogRequest = api.GetRegionsAsync(CancellationToken.None);
            while (!catalogRequest.IsCompleted) yield return null;
            var catalog = catalogRequest.Result;
            Assert.IsTrue(
                catalog.IsSuccess,
                catalog.Error == null
                    ? "Catalog request failed."
                    : $"Catalog request failed ({catalog.Error.code}, HTTP {catalog.StatusCode}): {catalog.Error.message}");
            Assert.Greater(catalog.Value.total, 0);

            var challengeRequest = api.GetChallengesAsync(CancellationToken.None);
            while (!challengeRequest.IsCompleted) yield return null;
            Assert.IsTrue(challengeRequest.Result.IsSuccess, "Challenge catalog did not load.");
            var valleyChallenges = challengeRequest.Result.Value.items.FindAll(item =>
                item.publicContent != null && item.publicContent.questSlug == "variables-in-the-valley");
            Assert.AreEqual(5, valleyChallenges.Count);
            Assert.AreEqual(1, valleyChallenges[0].version);
            var exactVersion = api.GetChallengeAsync("valley-name-tag", 1, CancellationToken.None);
            while (!exactVersion.IsCompleted) yield return null;
            Assert.IsTrue(exactVersion.Result.IsSuccess, "Exact published challenge version did not load.");

            var profileRequest = api.GetMyProfileAsync(CancellationToken.None);
            while (!profileRequest.IsCompleted) yield return null;
            Assert.IsFalse(profileRequest.Result.IsSuccess);
            Assert.Contains(profileRequest.Result.Error.code, new[] { "authentication_required", "authentication_not_configured" });
            Assert.Contains(profileRequest.Result.StatusCode, new[] { 401, 503 });
            Object.Destroy(settings);
        }

        private sealed class FixedInput : IGameInput
        {
            public Vector2 Move { get; set; }
            public Vector2 Look => Vector2.zero;
            public bool RunHeld => false;
            public bool JumpPressed => false;
            public bool InteractPressed => false;
        }
    }

    public sealed class PlayModeTestInteractable : MonoBehaviour, IInteractable
    {
        public int InteractionCount { get; private set; }
        private string _id = "test";
        private bool _available = true;
        public void Configure(string id, bool available) { _id = id; _available = available; }
        public string InteractionId => _id;
        public string InteractionPrompt => "Test interaction";
        public string UnavailableReason => "Unavailable for test";
        public bool CanInteract => _available;
        public bool IsAvailable => _available;
        public int SelectionPriority => 0;
        public void Interact(GameObject interactor) => InteractionCount++;
    }
}
