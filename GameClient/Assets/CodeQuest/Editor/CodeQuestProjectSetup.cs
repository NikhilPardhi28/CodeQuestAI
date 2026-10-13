using System.IO;
using CodeQuest.Networking;
using CodeQuest.UI;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace CodeQuest.Editor
{
    public static class CodeQuestProjectSetup
    {
        private const string Root = "Assets/CodeQuest";
        private const string SettingsFolder = Root + "/Settings";
        private const string ResourcesFolder = "Assets/Resources";
        private const string SceneFolder = "Assets/Scenes";
        private const string ScenePath = SceneFolder + "/Bootstrap.unity";

        [MenuItem("CodeQuest/Setup URP and Bootstrap Scene")]
        public static void SetupProject()
        {
            EnsureFolder("Assets", "CodeQuest");
            EnsureFolder(Root, "Settings");
            EnsureFolder("Assets", "Resources");
            EnsureFolder("Assets", "Scenes");
            EnsureApiSettings();
            EnsureUrp();
            EnsureBootstrapScene();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EditorUtility.DisplayDialog("CodeQuest project ready",
                "URP settings, API configuration, and the Bootstrap scene are ready. Open Assets/Scenes/Bootstrap.unity and press Play.", "OK");
        }

        private static void EnsureApiSettings()
        {
            const string path = ResourcesFolder + "/ApiClientSettings.asset";
            if (AssetDatabase.LoadAssetAtPath<ApiClientSettings>(path) != null) return;
            var settings = ScriptableObject.CreateInstance<ApiClientSettings>();
            AssetDatabase.CreateAsset(settings, path);
        }

        private static void EnsureUrp()
        {
            if (GraphicsSettings.defaultRenderPipeline != null) return;
            const string rendererPath = SettingsFolder + "/CodeQuestRenderer.asset";
            const string pipelinePath = SettingsFolder + "/CodeQuestUniversalRenderPipeline.asset";
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
            if (renderer == null)
            {
                renderer = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(renderer, rendererPath);
            }
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(pipelinePath);
            if (pipeline == null)
            {
                pipeline = UniversalRenderPipelineAsset.Create(renderer);
                AssetDatabase.CreateAsset(pipeline, pipelinePath);
            }
            GraphicsSettings.defaultRenderPipeline = pipeline;
            QualitySettings.renderPipeline = pipeline;
        }

        private static void EnsureBootstrapScene()
        {
            var scene = AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath);
            if (scene == null)
            {
                var newScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                new GameObject("CodeQuest Bootstrap").AddComponent<CodeQuestBootstrap>();
                EditorSceneManager.SaveScene(newScene, ScenePath);
            }
            var exists = false;
            foreach (var buildScene in EditorBuildSettings.scenes)
                if (buildScene.path == ScenePath) exists = true;
            if (!exists)
            {
                var scenes = new EditorBuildSettingsScene[EditorBuildSettings.scenes.Length + 1];
                EditorBuildSettings.scenes.CopyTo(scenes, 0);
                scenes[scenes.Length - 1] = new EditorBuildSettingsScene(ScenePath, true);
                EditorBuildSettings.scenes = scenes;
            }
            var bootstrap = AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath);
            if (bootstrap != null) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        private static void EnsureFolder(string parent, string name)
        {
            var path = parent + "/" + name;
            if (!AssetDatabase.IsValidFolder(path)) AssetDatabase.CreateFolder(parent, name);
        }

        [MenuItem("CodeQuest/Build Windows Player")]
        public static void BuildWindowsPlayer()
        {
            var buildFolder = @"D:\CodeQuestAI\Builds\Windows";
            if (!Directory.Exists(buildFolder)) Directory.CreateDirectory(buildFolder);
            var buildPath = Path.Combine(buildFolder, "CodeQuestAI.exe");

            var buildPlayerOptions = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = buildPath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None
            };

            var report = BuildPipeline.BuildPlayer(buildPlayerOptions);
            var summary = report.summary;

            File.WriteAllText(@"D:\CodeQuestAI\build_summary.txt",
                $"Result: {summary.result}\nTotalErrors: {summary.totalErrors}\nTotalWarnings: {summary.totalWarnings}\nTotalSize: {summary.totalSize} bytes\nOutputPath: {buildPath}\nDuration: {summary.totalTime}\n");

            if (summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
            {
                Debug.Log($"[CodeQuest] Build succeeded: {buildPath} ({summary.totalSize} bytes)");
            }
            else
            {
                Debug.LogError($"[CodeQuest] Build failed with result: {summary.result}");
            }
        }
    }
}
