using System;
using System.Threading;
using System.Threading.Tasks;
using CodeQuest.Core;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Networking;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace CodeQuest.UI
{
    public sealed class RuntimeHud : IDisposable
    {
        private readonly CodeQuestApiClient _api;
        private readonly IGameStateService _gameState;
        private readonly IInteractionSource _interaction;
        private readonly CancellationTokenSource _lifetime = new CancellationTokenSource();
        private CancellationTokenSource _request;
        private GameObject _menu;
        private GameObject _catalog;
        private GameObject _profile;
        private Text _status;
        private Text _catalogText;
        private Text _profileText;
        private Text _interactionText;

        public RuntimeHud(CodeQuestApiClient api, IGameStateService gameState, IInteractionSource interaction, Transform root)
        {
            _api = api;
            _gameState = gameState;
            _interaction = interaction;
            Build(root);
            _ = CheckConnectionAsync();
        }

        public void Tick()
        {
            if (_interactionText != null) _interactionText.text = string.IsNullOrWhiteSpace(_interaction.CurrentPrompt) ? string.Empty : "E  " + _interaction.CurrentPrompt;
        }

        public void ToggleMenu()
        {
            if (_menu == null) return;
            var showing = !_menu.activeSelf;
            _catalog.SetActive(false);
            _profile.SetActive(false);
            _menu.SetActive(showing);
            if (!_menu.activeSelf) _gameState.ChangeTo(GameState.InWorld);
            else _gameState.ChangeTo(GameState.MainMenu);
            Cursor.lockState = _menu.activeSelf ? CursorLockMode.None : CursorLockMode.Locked;
            Cursor.visible = _menu.activeSelf;
        }

        public void Dispose()
        {
            _lifetime.Cancel();
            _request?.Cancel();
            _request?.Dispose();
            _lifetime.Dispose();
        }

        private void Build(Transform root)
        {
            if (UnityEngine.Object.FindObjectOfType<EventSystem>() == null)
            {
                var eventSystem = new GameObject("Event System", typeof(EventSystem));
                eventSystem.transform.SetParent(root, false);
                eventSystem.AddComponent<StandaloneInputModule>();
            }
            var canvasObject = new GameObject("CodeQuest UI", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvasObject.transform.SetParent(root, false);
            var canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var scaler = canvasObject.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280f, 720f);
            _status = MakeText(canvasObject.transform, "Connection status", new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(20f, -22f), new Vector2(500f, 36f), 18, TextAnchor.UpperLeft);
            _interactionText = MakeText(canvasObject.transform, "Interaction prompt", new Vector2(.5f, 0f), new Vector2(.5f, 0f), new Vector2(0f, 72f), new Vector2(700f, 40f), 20, TextAnchor.MiddleCenter);
            _menu = MakePanel(canvasObject.transform, "Main Menu");
            MakeText(_menu.transform, "Title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -90f), new Vector2(720f, 72f), 36, TextAnchor.MiddleCenter).text = "CodeQuest AI";
            MakeText(_menu.transform, "Instructions", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -144f), new Vector2(900f, 40f), 18, TextAnchor.MiddleCenter).text = "WASD move  •  Mouse look  •  Shift run  •  Space jump  •  E interact  •  Esc menu";
            MakeButton(_menu.transform, "Start", "Start exploring", new Vector2(0f, -220f), () => ToggleMenu());
            MakeButton(_menu.transform, "Open catalog", "Curriculum catalog", new Vector2(0f, -280f), () => ShowCatalog(true));
            MakeButton(_menu.transform, "Open profile", "Player profile", new Vector2(0f, -340f), () => ShowProfile(true));
            _catalog = MakePanel(canvasObject.transform, "Catalog");
            MakeText(_catalog.transform, "Catalog title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -56f), new Vector2(700f, 56f), 28, TextAnchor.MiddleCenter).text = "Connected curriculum";
            _catalogText = MakeText(_catalog.transform, "Catalog results", new Vector2(.5f, .5f), new Vector2(.5f, .5f), Vector2.zero, new Vector2(720f, 360f), 18, TextAnchor.UpperLeft);
            _catalogText.alignment = TextAnchor.UpperLeft;
            MakeButton(_catalog.transform, "Refresh catalog", "Refresh catalog", new Vector2(-140f, -230f), () => _ = LoadCatalogAsync());
            MakeButton(_catalog.transform, "Close catalog", "Close", new Vector2(140f, -230f), () => ShowCatalog(false));
            _profile = MakePanel(canvasObject.transform, "Profile");
            MakeText(_profile.transform, "Profile title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -56f), new Vector2(700f, 56f), 28, TextAnchor.MiddleCenter).text = "Player profile";
            _profileText = MakeText(_profile.transform, "Profile result", new Vector2(.5f, .5f), new Vector2(.5f, .5f), Vector2.zero, new Vector2(720f, 300f), 20, TextAnchor.MiddleCenter);
            MakeButton(_profile.transform, "Load profile", "Load profile", new Vector2(-140f, -190f), () => _ = LoadProfileAsync());
            MakeButton(_profile.transform, "Close profile", "Close", new Vector2(140f, -190f), () => ShowProfile(false));
            _catalog.SetActive(false);
            _profile.SetActive(false);
            _status.text = "Connecting to CodeQuest backend…";
        }

        private async Task CheckConnectionAsync()
        {
            BeginRequest();
            var token = _request.Token;
            var health = await _api.GetHealthAsync(token);
            if (!_lifetime.IsCancellationRequested)
                _status.text = health.IsSuccess ? "Backend: online" : "Backend: " + health.Error.message;
            if (health.IsSuccess)
            {
                var readiness = await _api.GetReadinessAsync(token);
                if (!_lifetime.IsCancellationRequested)
                    _status.text = readiness.IsSuccess ? "Backend: online • database ready" : "Backend: online • " + readiness.Error.message;
            }
        }

        private async Task LoadCatalogAsync()
        {
            BeginRequest();
            _catalogText.text = "Loading curriculum and quest catalog…";
            var token = _request.Token;
            try
            {
                var regions = await _api.GetRegionsAsync(token);
                if (!regions.IsSuccess) { _catalogText.text = "Could not load regions. " + regions.Error.message; return; }
                var quests = await _api.GetQuestsAsync(token);
                if (!quests.IsSuccess) { _catalogText.text = "Could not load quests. " + quests.Error.message; return; }
                var challenges = await _api.GetChallengesAsync(token);
                if (!challenges.IsSuccess) { _catalogText.text = "Could not load challenges. " + challenges.Error.message; return; }
                var result = "REGIONS\n";
                foreach (var region in regions.Value.items) result += "• " + region.name + " — " + region.summary + "\n";
                result += "\nQUESTS\n";
                foreach (var quest in quests.Value.items) result += "• " + quest.title + " — " + quest.summary + "\n";
                result += "\nCHALLENGES\n";
                foreach (var challenge in challenges.Value.items) result += "• " + challenge.title + " — " + challenge.statement + "\n";
                _catalogText.text = result;
            }
            catch (OperationCanceledException) { _catalogText.text = "Catalog request cancelled."; }
        }

        private async Task LoadProfileAsync()
        {
            BeginRequest();
            _profileText.text = "Checking sign-in…";
            try
            {
                var result = await _api.GetMyProfileAsync(_request.Token);
                if (result.IsSuccess)
                    _profileText.text = result.Value.displayName + "\n" + result.Value.locale + "\nProfile ID: " + result.Value.id;
                else if (result.Error.code == "authentication_required")
                    _profileText.text = "Sign in is required to view this profile. The OIDC provider is not configured in this milestone.";
                else if (result.Error.code == "invalid_bearer_token")
                    _profileText.text = "Your sign-in session is invalid or expired. Sign in again.";
                else
                    _profileText.text = result.Error.message;
            }
            catch (OperationCanceledException) { _profileText.text = "Profile request cancelled."; }
        }

        private void BeginRequest()
        {
            _request?.Cancel();
            _request?.Dispose();
            _request = CancellationTokenSource.CreateLinkedTokenSource(_lifetime.Token);
        }

        private void ShowCatalog(bool visible)
        {
            _catalog.SetActive(visible);
            if (visible) { _menu.SetActive(false); _profile.SetActive(false); _ = LoadCatalogAsync(); }
            else _menu.SetActive(true);
        }

        private void ShowProfile(bool visible)
        {
            _profile.SetActive(visible);
            if (visible) { _menu.SetActive(false); _catalog.SetActive(false); _ = LoadProfileAsync(); }
            else _menu.SetActive(true);
        }

        private static GameObject MakePanel(Transform parent, string name)
        {
            var panel = new GameObject(name, typeof(RectTransform), typeof(Image));
            panel.transform.SetParent(parent, false);
            var rect = panel.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(.5f, .5f);
            rect.anchorMax = new Vector2(.5f, .5f);
            rect.sizeDelta = new Vector2(850f, 560f);
            rect.anchoredPosition = Vector2.zero;
            panel.GetComponent<Image>().color = new Color(.035f, .055f, .09f, .94f);
            return panel;
        }

        private static Text MakeText(Transform parent, string name, Vector2 anchorMin, Vector2 anchorMax, Vector2 position, Vector2 size, int fontSize, TextAnchor alignment)
        {
            var textObject = new GameObject(name, typeof(RectTransform), typeof(Text));
            textObject.transform.SetParent(parent, false);
            var rect = textObject.GetComponent<RectTransform>();
            rect.anchorMin = anchorMin;
            rect.anchorMax = anchorMax;
            rect.sizeDelta = size;
            rect.anchoredPosition = position;
            var text = textObject.GetComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = fontSize;
            text.color = Color.white;
            text.alignment = alignment;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            return text;
        }

        private static void MakeButton(Transform parent, string name, string label, Vector2 position, Action onClick)
        {
            var buttonObject = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            buttonObject.transform.SetParent(parent, false);
            var rect = buttonObject.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(.5f, 1f);
            rect.anchorMax = new Vector2(.5f, 1f);
            rect.sizeDelta = new Vector2(250f, 48f);
            rect.anchoredPosition = position;
            buttonObject.GetComponent<Image>().color = new Color(.12f, .35f, .57f, 1f);
            buttonObject.GetComponent<Button>().onClick.AddListener(() => onClick());
            var text = MakeText(buttonObject.transform, label, Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero, 18, TextAnchor.MiddleCenter);
            text.rectTransform.offsetMin = Vector2.zero;
            text.rectTransform.offsetMax = Vector2.zero;
        }

    }
}
