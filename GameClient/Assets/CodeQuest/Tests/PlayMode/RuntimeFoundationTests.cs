using System.Collections;
using System;
using System.Reflection;
using System.Threading;
using CodeQuest.Gameplay.Camera;
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
            Assert.IsTrue(interactor.TryInteract());
            Assert.AreEqual(1, interactable.InteractionCount);
            Object.Destroy(player);
            Object.Destroy(target);
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
            Assert.IsTrue(catalog.IsSuccess, catalog.Error == null ? "Catalog request failed." : catalog.Error.message);
            Assert.Greater(catalog.Value.total, 0);

            var profileRequest = api.GetMyProfileAsync(CancellationToken.None);
            while (!profileRequest.IsCompleted) yield return null;
            Assert.IsFalse(profileRequest.Result.IsSuccess);
            Assert.AreEqual("authentication_required", profileRequest.Result.Error.code);
            Assert.AreEqual(401, profileRequest.Result.StatusCode);
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
        public string InteractionPrompt => "Test interaction";
        public bool CanInteract => true;
        public void Interact(GameObject interactor) => InteractionCount++;
    }
}
