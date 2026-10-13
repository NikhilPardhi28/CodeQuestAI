using System.Collections.Generic;
using System.IO;
using CodeQuest.Gameplay.Player;
using UnityEditor;
using UnityEngine;

namespace CodeQuest.Editor
{
    public static class KenneyDiagnosticInspector
    {
        [InitializeOnLoadMethod]
        [MenuItem("CodeQuest/Diagnose Kenney Legs")]
        public static void RunDiagnosis()
        {
            var config = AssetDatabase.LoadAssetAtPath<KenneyCharacterVisualConfig>(
                "Assets/Resources/Kenney/KenneyCharacterVisualConfig.asset");
            if (config == null || config.characterModel == null)
            {
                Debug.LogError("[KenneyDiag] Config or characterModel is null!");
                return;
            }

            var reportPath = @"D:\CodeQuestAI\kenney_diagnostic_report.txt";
            var lines = new List<string>();
            lines.Add("=== KENNEY RUNTIME / EDIT DIAGNOSTIC REPORT ===");

            // 1. Inspect Model Prefab / Hierarchy directly
            var prefab = config.characterModel;
            lines.Add($"Model Prefab: {prefab.name}");
            var smrPrefab = prefab.GetComponentInChildren<SkinnedMeshRenderer>();
            lines.Add($"SMR on Prefab: {smrPrefab != null}, mesh={smrPrefab?.sharedMesh?.name}, bonesCount={smrPrefab?.bones?.Length}, rootBone={smrPrefab?.rootBone?.name}");
            lines.Add($"SMR bounds on Prefab: center={smrPrefab?.bounds.center}, extents={smrPrefab?.bounds.extents}, min={smrPrefab?.bounds.min}, max={smrPrefab?.bounds.max}");
            lines.Add($"SMR localBounds on Prefab: center={smrPrefab?.localBounds.center}, extents={smrPrefab?.localBounds.extents}");

            // 2. Instantiate Player as in CodeQuestBootstrap
            var playerRoot = new GameObject("DiagPlayerRoot");
            try
            {
                // In Bootstrap, Player is at position (0, 1, 0)
                playerRoot.transform.position = new Vector3(0f, 1f, 0f);
                var controller = playerRoot.AddComponent<CharacterController>();
                controller.center = Vector3.zero;
                controller.height = 2f;
                controller.radius = 0.5f;

                var motor = playerRoot.AddComponent<ThirdPersonMotor>();

                var visual = Object.Instantiate(config.characterModel, playerRoot.transform);
                visual.name = "PlayerKenneyVisual";
                // Current bootstrap localPosition
                visual.transform.localPosition = new Vector3(0f, -0.88f, 0f);
                visual.transform.localRotation = Quaternion.identity;
                visual.transform.localScale = Vector3.one;

                var smr = visual.GetComponentInChildren<SkinnedMeshRenderer>();
                if (config.humanMaleMaterial != null) smr.sharedMaterial = config.humanMaleMaterial;

                if (smr.rootBone == null)
                {
                    var rootBone = visual.transform.Find("Root/HipsCtrl") ?? visual.transform.Find("Root");
                    if (rootBone != null) smr.rootBone = rootBone;
                }
                smr.updateWhenOffscreen = true;
                smr.localBounds = new Bounds(new Vector3(0f, 0.9f, 0f), new Vector3(2f, 2.2f, 2f));

                var animator = visual.GetComponent<Animator>();
                if (animator == null) animator = visual.AddComponent<Animator>();
                animator.avatar = config.characterAvatar;
                animator.runtimeAnimatorController = config.animatorController;
                animator.applyRootMotion = false;
                motor.BindAnimator(animator);

                lines.Add($"Player Root World Pos: {playerRoot.transform.position}");
                lines.Add($"Visual Local Pos: {visual.transform.localPosition}");
                lines.Add($"Visual World Pos: {visual.transform.position}");
                lines.Add($"Controller bounds: min={controller.bounds.min}, max={controller.bounds.max}, center={controller.bounds.center}");
                lines.Add($"Ground plane Y = 0.0f; Valley Path surface Y = 0.03 + 0.06/2 = 0.06f");

                // Check all bone transforms under Root
                var hips = visual.transform.Find("Root/HipsCtrl/Hips");
                var leftUpLeg = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg");
                var leftLeg = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg/LeftLeg");
                var leftFoot = visual.transform.Find("Root/HipsCtrl/Hips/LeftUpLeg/LeftLeg/LeftFoot");
                var rightUpLeg = visual.transform.Find("Root/HipsCtrl/Hips/RightUpLeg");
                var rightLeg = visual.transform.Find("Root/HipsCtrl/Hips/RightUpLeg/RightLeg");
                var rightFoot = visual.transform.Find("Root/HipsCtrl/Hips/RightUpLeg/RightLeg/RightFoot");

                // Also check if there are other bone structures under Root!
                lines.Add("--- Children of Root ---");
                var rootTr = visual.transform.Find("Root");
                if (rootTr != null)
                {
                    for (int i = 0; i < rootTr.childCount; i++)
                    {
                        var ch = rootTr.GetChild(i);
                        lines.Add($"  Root child [{i}]: {ch.name}, localPos={ch.localPosition}, localScale={ch.localScale}");
                    }
                }

                // Function to record state
                void RecordBoneState(string stateName)
                {
                    lines.Add($"=== State: {stateName} ===");
                    lines.Add($"  SMR bounds: center={smr.bounds.center}, min={smr.bounds.min}, max={smr.bounds.max}");
                    lines.Add($"  Hips: worldPos={hips?.position}, localPos={hips?.localPosition}, localScale={hips?.localScale}");
                    lines.Add($"  LeftUpLeg: worldPos={leftUpLeg?.position}, localPos={leftUpLeg?.localPosition}, localScale={leftUpLeg?.localScale}");
                    lines.Add($"  LeftLeg: worldPos={leftLeg?.position}, localPos={leftLeg?.localPosition}, localScale={leftLeg?.localScale}");
                    lines.Add($"  LeftFoot: worldPos={leftFoot?.position}, localPos={leftFoot?.localPosition}, localScale={leftFoot?.localScale}");
                    lines.Add($"  RightFoot: worldPos={rightFoot?.position}, localPos={rightFoot?.localPosition}, localScale={rightFoot?.localScale}");
                }

                // State A: Bind Pose (Animator disabled)
                animator.enabled = false;
                RecordBoneState("A - Animator Disabled (Bind Pose)");

                // State B: Idle
                animator.enabled = true;
                animator.Play("Idle", 0, 0f);
                animator.Update(0f);
                RecordBoneState("B - Idle 0.0s");

                animator.Update(0.5f);
                RecordBoneState("B - Idle 0.5s");

                // State C: Run
                animator.Play("Run", 0, 0f);
                animator.Update(0f);
                RecordBoneState("C - Run 0.0s");

                animator.Update(0.3f);
                RecordBoneState("C - Run 0.3s");

                // State D: Jump
                animator.Play("Jump", 0, 0f);
                animator.Update(0f);
                RecordBoneState("D - Jump 0.0s");

                animator.Update(0.25f);
                RecordBoneState("D - Jump 0.25s");

                // Check SMR bones array
                lines.Add("--- SMR Bones Array ---");
                lines.Add($"smr.bones length = {smr.bones.Length}");
                for (int i = 0; i < smr.bones.Length; i++)
                {
                    var b = smr.bones[i];
                    if (b != null && (b.name.Contains("Leg") || b.name.Contains("Foot") || b.name.Contains("Hips") || b.name.Contains("Root")))
                    {
                        lines.Add($"  Bone[{i}] {b.name}: worldPos={b.position}, localScale={b.localScale}");
                    }
                }

                // Check materials and submeshes
                lines.Add("--- SMR Mesh & Submeshes ---");
                lines.Add($"sharedMesh name: {smr.sharedMesh.name}, subMeshCount: {smr.sharedMesh.subMeshCount}");
                for (int m = 0; m < smr.sharedMesh.subMeshCount; m++)
                {
                    var desc = smr.sharedMesh.GetSubMesh(m);
                    lines.Add($"  Submesh {m}: indexCount={desc.indexCount}, baseVertex={desc.baseVertex}, firstVertex={desc.firstVertex}, vertexCount={desc.vertexCount}, bounds={desc.bounds}");
                }
                lines.Add($"sharedMaterials length: {smr.sharedMaterials.Length}");
                for (int mi = 0; mi < smr.sharedMaterials.Length; mi++)
                {
                    lines.Add($"  Material [{mi}]: {smr.sharedMaterials[mi]?.name}, shader={smr.sharedMaterials[mi]?.shader?.name}");
                }

                File.WriteAllLines(reportPath, lines);
                Debug.Log($"[KenneyDiag] Diagnosis completed and written to {reportPath}");
            }
            finally
            {
                Object.DestroyImmediate(playerRoot);
            }
        }
    }
}
