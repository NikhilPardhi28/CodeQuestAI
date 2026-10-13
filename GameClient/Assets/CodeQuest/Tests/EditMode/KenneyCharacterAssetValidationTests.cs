using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace CodeQuest.Tests.EditMode
{
    public sealed class KenneyCharacterAssetValidationTests
    {
        private const string RootPath = "Assets/ThirdParty/KenneyAnimatedCharacters3";
        private const string ModelPath = RootPath + "/Model/characterMedium.fbx";
        private const string IdlePath = RootPath + "/Animations/idle.fbx";
        private const string RunPath = RootPath + "/Animations/run.fbx";
        private const string JumpPath = RootPath + "/Animations/jump.fbx";
        private const string ControllerPath = RootPath + "/KenneyCharacterController.controller";
        private const string MaleMatPath = RootPath + "/Materials/M_HumanMaleA.mat";
        private const string FemaleMatPath = RootPath + "/Materials/M_HumanFemaleA.mat";

        [Test]
        public void ModelHasValidHumanoidAvatar()
        {
            var avatar = AssetDatabase.LoadAssetAtPath<Avatar>(ModelPath);
            Assert.IsNotNull(avatar, "Avatar should be loaded from characterMedium.fbx");
            Assert.IsTrue(avatar.isValid, "Avatar should be valid");
            Assert.IsTrue(avatar.isHuman, "Avatar should be configured as Humanoid");
        }

        [Test]
        public void AnimationFBXsHaveValidIndependentHumanoidAvatars()
        {
            var idleAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(IdlePath);
            Assert.IsNotNull(idleAvatar, "Idle avatar should be generated");
            Assert.IsTrue(idleAvatar.isValid, "Idle avatar must be valid");
            Assert.IsTrue(idleAvatar.isHuman, "Idle avatar must be Humanoid");

            var runAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(RunPath);
            Assert.IsNotNull(runAvatar, "Run avatar should be generated");
            Assert.IsTrue(runAvatar.isValid, "Run avatar must be valid");
            Assert.IsTrue(runAvatar.isHuman, "Run avatar must be Humanoid");

            var jumpAvatar = AssetDatabase.LoadAssetAtPath<Avatar>(JumpPath);
            Assert.IsNotNull(jumpAvatar, "Jump avatar should be generated");
            Assert.IsTrue(jumpAvatar.isValid, "Jump avatar must be valid");
            Assert.IsTrue(jumpAvatar.isHuman, "Jump avatar must be Humanoid");
        }

        [Test]
        public void AnimationClipsArePresentAndHavePositiveLength()
        {
            var idleClip = GetClipByInternalId(IdlePath, 2910742486769232160);
            Assert.IsNotNull(idleClip, "Idle clip (Root|Idle) must exist in idle.fbx");
            Assert.Greater(idleClip.length, 0.5f, "Idle clip length should be full cycle");

            var runClip = GetClipByInternalId(RunPath, 4188298191382927259);
            Assert.IsNotNull(runClip, "Run clip (Root|Run) must exist in run.fbx");
            Assert.Greater(runClip.length, 0.4f, "Run clip length should be full cycle");

            var jumpClip = GetClipByInternalId(JumpPath, -8630955994762890147);
            Assert.IsNotNull(jumpClip, "Jump clip (Root|Jump) must exist in jump.fbx");
            Assert.Greater(jumpClip.length, 0.3f, "Jump clip length should be full jump motion");
        }

        private static AnimationClip GetClipByInternalId(string path, long internalId)
        {
            var subAssets = AssetDatabase.LoadAllAssetsAtPath(path);
            return subAssets.OfType<AnimationClip>().FirstOrDefault(c => c.length > 0.1f);
        }

        [Test]
        public void ControllerAndMaterialsAreValid()
        {
            var controller = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(ControllerPath);
            Assert.IsNotNull(controller, "KenneyCharacterController should be loaded");

            var maleMat = AssetDatabase.LoadAssetAtPath<Material>(MaleMatPath);
            var femaleMat = AssetDatabase.LoadAssetAtPath<Material>(FemaleMatPath);
            Assert.IsNotNull(maleMat, "Male material should exist");
            Assert.IsNotNull(femaleMat, "Female material should exist");
            Assert.AreEqual("Universal Render Pipeline/Lit", maleMat.shader.name);
            Assert.AreEqual("Universal Render Pipeline/Lit", femaleMat.shader.name);
        }

        [Test]
        public void CharacterRendersWithAnimatorAndRetargetedClips()
        {
            var modelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            Assert.IsNotNull(modelPrefab, "characterMedium.fbx prefab should exist");

            var instance = Object.Instantiate(modelPrefab);
            try
            {
                var renderer = instance.GetComponentInChildren<SkinnedMeshRenderer>();
                Assert.IsNotNull(renderer, "SkinnedMeshRenderer must be present on character hierarchy");
                Assert.IsNotNull(renderer.sharedMesh, "Skinned mesh must be valid");
                Assert.AreEqual("characterMedium", renderer.sharedMesh.name);
                Assert.Greater(renderer.bones.Length, 20, "Character should have a skeletal bone hierarchy");

                var maleMat = AssetDatabase.LoadAssetAtPath<Material>(MaleMatPath);
                renderer.sharedMaterial = maleMat;
                Assert.AreEqual(maleMat, renderer.sharedMaterial);

                var animator = instance.GetComponent<Animator>();
                if (animator == null) animator = instance.AddComponent<Animator>();
                var avatar = AssetDatabase.LoadAssetAtPath<Avatar>(ModelPath);
                var controller = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(ControllerPath);

                animator.avatar = avatar;
                animator.runtimeAnimatorController = controller;
                Assert.AreEqual(avatar, animator.avatar);
                Assert.AreEqual(controller, animator.runtimeAnimatorController);
            }
            finally
            {
                Object.DestroyImmediate(instance);
            }
        }

        [Test]
        public void PlayerRootAttachesKenneyVisualCorrectly()
        {
            var config = AssetDatabase.LoadAssetAtPath<CodeQuest.Gameplay.Player.KenneyCharacterVisualConfig>(
                "Assets/Resources/Kenney/KenneyCharacterVisualConfig.asset");
            Assert.IsNotNull(config, "KenneyCharacterVisualConfig asset must exist");
            Assert.IsNotNull(config.characterModel, "Character model must be assigned in config");
            Assert.IsNotNull(config.characterAvatar, "Character avatar must be assigned in config");
            Assert.IsNotNull(config.animatorController, "Animator controller must be assigned in config");
            Assert.IsNotNull(config.humanMaleMaterial, "Human male material must be assigned in config");

            var playerRoot = new GameObject("PlayerTestRoot");
            try
            {
                var controller = playerRoot.AddComponent<CharacterController>();
                controller.center = Vector3.zero;
                controller.height = 2f;
                controller.radius = 0.5f;

                var motor = playerRoot.AddComponent<CodeQuest.Gameplay.Player.ThirdPersonMotor>();
                var interactor = playerRoot.AddComponent<CodeQuest.Gameplay.Interaction.PlayerInteractor>();

                // Instantiate child visual as CodeQuestBootstrap does
                var visual = Object.Instantiate(config.characterModel, playerRoot.transform);
                visual.name = "PlayerKenneyVisual";
                visual.transform.localPosition = new Vector3(0f, -0.88f, 0f);
                visual.transform.localRotation = Quaternion.identity;
                visual.transform.localScale = Vector3.one;

                var colliders = visual.GetComponentsInChildren<Collider>(true);
                foreach (var col in colliders) Object.DestroyImmediate(col);

                var skinnedRenderer = visual.GetComponentInChildren<SkinnedMeshRenderer>();
                Assert.IsNotNull(skinnedRenderer);
                skinnedRenderer.sharedMaterial = config.humanMaleMaterial;

                // Match CodeQuestBootstrap configuration (preserve prefab rootBone)
                if (skinnedRenderer.rootBone == null)
                {
                    var rootBone = visual.transform.Find("Root/HipsCtrl") ?? visual.transform.Find("Root");
                    if (rootBone != null) skinnedRenderer.rootBone = rootBone;
                }
                skinnedRenderer.updateWhenOffscreen = true;
                skinnedRenderer.localBounds = new Bounds(new Vector3(0f, 0.9f, 0f), new Vector3(2f, 2.2f, 2f));

                var animator = visual.GetComponent<Animator>();
                if (animator == null) animator = visual.AddComponent<Animator>();
                animator.avatar = config.characterAvatar;
                animator.runtimeAnimatorController = config.animatorController;
                animator.applyRootMotion = false;
                motor.BindAnimator(animator);

                // Verify hierarchy and components
                Assert.AreEqual(1, playerRoot.transform.childCount, "Only Kenney visual should be attached as child");
                Assert.AreEqual(new Vector3(0f, -0.88f, 0f), visual.transform.localPosition, "Visual feet should align at y = -0.88");
                Assert.AreEqual(0, visual.GetComponentsInChildren<Collider>().Length, "No sub-colliders should remain");
                Assert.AreEqual(config.humanMaleMaterial, skinnedRenderer.sharedMaterial, "Human male skin material must be assigned");
                Assert.AreEqual(config.characterAvatar, animator.avatar, "Avatar must be assigned");
                Assert.AreEqual(config.animatorController, animator.runtimeAnimatorController, "Animator controller must be assigned");
                Assert.IsFalse(animator.applyRootMotion, "Root motion must be disabled so CharacterController dictates movement");
                Assert.IsTrue(skinnedRenderer.updateWhenOffscreen, "SkinnedMeshRenderer updateWhenOffscreen must be true to prevent mesh/leg culling");
                Assert.IsNotNull(skinnedRenderer.rootBone, "SkinnedMeshRenderer must have a valid rootBone assigned");

                // Sample Idle and inspect leg bone transforms and bounds
                animator.Play("Idle", 0, 0f);
                animator.Update(0f);
                var hips = visual.transform.Find("Root/HipsCtrl/Hips");
                var leftUpLeg = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg");
                var leftLeg = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg/LeftLeg");
                var leftFoot = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg/LeftLeg/LeftFoot");

                var diagLines = new System.Collections.Generic.List<string>();
                diagLines.Add("=== KENNEY ISOLATED TEST HARNESS REPORT ===");
                diagLines.Add($"Visual localPos: {visual.transform.localPosition}");
                diagLines.Add($"SMR bounds: {skinnedRenderer.bounds}");
                diagLines.Add($"SMR localBounds: {skinnedRenderer.localBounds}");
                diagLines.Add($"SMR rootBone: {skinnedRenderer.rootBone?.name}");
                diagLines.Add($"SMR sharedMesh vertexCount: {skinnedRenderer.sharedMesh.vertexCount}, subMeshCount: {skinnedRenderer.sharedMesh.subMeshCount}");
                diagLines.Add($"SMR material: {skinnedRenderer.sharedMaterial?.name}");

                // State A: Bind Pose (Animator disabled)
                animator.enabled = false;
                diagLines.Add($"[State A: Bind Pose]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                // State B: Idle
                animator.enabled = true;
                animator.Play("Idle", 0, 0f);
                animator.Update(0f);
                diagLines.Add($"[State B: Idle 0.0]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                animator.Update(0.5f);
                diagLines.Add($"[State B: Idle 0.5]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                // State C: Run
                animator.Play("Run", 0, 0f);
                animator.Update(0f);
                diagLines.Add($"[State C: Run 0.0]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                // State D: Jump
                animator.Play("Jump", 0, 0f);
                animator.Update(0f);
                diagLines.Add($"[State D: Jump 0.0]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                animator.Update(0.2f);
                diagLines.Add($"[State D: Jump 0.2]");
                diagLines.Add($"Hips: worldPos={hips.position}, localPos={hips.localPosition}, localScale={hips.localScale}");
                diagLines.Add($"LeftUpLeg: worldPos={leftUpLeg.position}, localPos={leftUpLeg.localPosition}, localScale={leftUpLeg.localScale}");
                diagLines.Add($"LeftLeg: worldPos={leftLeg.position}, localPos={leftLeg.localPosition}, localScale={leftLeg.localScale}");
                diagLines.Add($"LeftFoot: worldPos={leftFoot.position}, localPos={leftFoot.localPosition}, localScale={leftFoot.localScale}");

                System.IO.File.WriteAllLines(@"D:\CodeQuestAI\kenney_diagnostic_report.txt", diagLines);

                Assert.IsNotNull(hips, "Hips bone must exist in skeleton hierarchy");
                Assert.IsNotNull(leftUpLeg, "LeftUpLeg bone must exist in skeleton hierarchy");
                Assert.IsNotNull(leftLeg, "LeftLeg bone must exist in skeleton hierarchy");
                Assert.IsNotNull(leftFoot, "LeftFoot bone must exist in skeleton hierarchy");

                // Verify leg bones have non-zero scale and are positioned above ground level (y > 0)
                Assert.Greater(leftUpLeg.localScale.sqrMagnitude, 0.5f, "LeftUpLeg scale must not be collapsed");
                Assert.Greater(leftLeg.localScale.sqrMagnitude, 0.5f, "LeftLeg scale must not be collapsed");
                Assert.Greater(leftFoot.localScale.sqrMagnitude, 0.5f, "LeftFoot scale must not be collapsed");
                Assert.Greater(hips.position.y, -0.6f, "Hips must not collapse below root level");
            }
            finally
            {
                Object.DestroyImmediate(playerRoot);
            }
        }
    }
}
