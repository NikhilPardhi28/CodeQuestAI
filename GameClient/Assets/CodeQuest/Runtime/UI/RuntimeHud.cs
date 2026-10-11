using System;
using System.Threading;
using System.Threading.Tasks;
using CodeQuest.Core;
using CodeQuest.Gameplay.Interaction;
using CodeQuest.Gameplay.Dialogue;
using CodeQuest.Gameplay.Quests;
using CodeQuest.Gameplay.Challenges;
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
        private readonly QuestService _quests;
        private readonly DialogueSession _dialogue;
        private readonly CancellationTokenSource _lifetime = new CancellationTokenSource();
        private CancellationTokenSource _request;
        private GameObject _menu;
        private GameObject _catalog;
        private GameObject _profile;
        private Text _status;
        private Text _catalogText;
        private Text _profileText;
        private Text _interactionText;
        private Text _objectiveNotification;
        private float _notificationUntil;
        private GameObject _journal;
        private GameObject _dialoguePanel;
        private Text _journalText;
        private Text _dialogueText;
        private Transform _dialogueChoices;
        private GameObject _challengePanel;
        private Text _challengeTitle;
        private Text _challengeInstructions;
        private Text _challengeFeedback;
        private InputField _challengeSource;
        private ChallengeDto _activeChallenge;
        private string _activeClientSubmissionId;
        private string _activeSubmissionSource;
        private string _activeSubmissionId;
        private int _nextHintLevel = 1;
        private readonly System.Collections.Generic.List<GameObject> _challengeButtons = new System.Collections.Generic.List<GameObject>();
        private readonly System.Collections.Generic.List<GameObject> _choiceButtons = new System.Collections.Generic.List<GameObject>();
        private bool _returnToMenu;
        private CursorLockMode _returnCursorLock;
        private bool _returnCursorVisible;

        public RuntimeHud(CodeQuestApiClient api, IGameStateService gameState, IInteractionSource interaction, QuestService quests, Transform root)
        {
            _api = api;
            _gameState = gameState;
            _interaction = interaction;
            _quests = quests;
            _dialogue = new DialogueSession(quests);
            _dialogue.EventRaised += eventId => _quests.RecordWorldEvent("dialogue:" + eventId, QuestObjectiveKind.DialogueEvent, eventId);
            _quests.ObjectiveNotification += ShowObjectiveNotification;
            _quests.Changed += OnQuestChanged;
            Build(root);
            _ = CheckConnectionAsync();
        }

        public void Tick()
        {
            if (_interactionText != null) _interactionText.text = string.IsNullOrWhiteSpace(_interaction.CurrentPrompt) ? string.Empty : "E  " + _interaction.CurrentPrompt;
            if (_objectiveNotification != null && Time.unscaledTime >= _notificationUntil) _objectiveNotification.text = string.Empty;
            var target = (_interaction as PlayerInteractor)?.CurrentTarget as NpcDialogueInteractable;
            if (target != null && UnityEngine.Input.GetKeyDown(KeyCode.E)) OpenDialogue(target.Definition);
            if (UnityEngine.Input.GetKeyDown(KeyCode.J)) ShowJournal(true);
            if (_dialoguePanel != null && _dialoguePanel.activeSelf && UnityEngine.Input.GetKeyDown(KeyCode.Escape)) CloseDialogue();
        }

        public void ToggleMenu()
        {
            if (_menu == null) return;
            var showing = !_menu.activeSelf;
            _catalog.SetActive(false);
            _profile.SetActive(false);
            _journal.SetActive(false);
            _dialoguePanel.SetActive(false);
            _challengePanel?.SetActive(false);
            _menu.SetActive(showing);
            if (!_menu.activeSelf) _gameState.ChangeTo(GameState.InWorld);
            else _gameState.ChangeTo(GameState.MainMenu);
            Cursor.lockState = _menu.activeSelf ? CursorLockMode.None : CursorLockMode.Locked;
            Cursor.visible = _menu.activeSelf;
        }

        public void Dispose()
        {
            _lifetime.Cancel();
            _quests.ObjectiveNotification -= ShowObjectiveNotification;
            _quests.Changed -= OnQuestChanged;
            _dialogue.Cancel();
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
            _objectiveNotification = MakeText(canvasObject.transform, "Objective notification", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -72f), new Vector2(800f, 42f), 18, TextAnchor.MiddleCenter);
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
            MakeButton(_catalog.transform, "Refresh catalog", "Refresh catalog", new Vector2(-140f, -265f), () => _ = LoadCatalogAsync());
            MakeButton(_catalog.transform, "Close catalog", "Close", new Vector2(140f, -265f), () => ShowCatalog(false));
            _profile = MakePanel(canvasObject.transform, "Profile");
            MakeText(_profile.transform, "Profile title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -56f), new Vector2(700f, 56f), 28, TextAnchor.MiddleCenter).text = "Player profile";
            _profileText = MakeText(_profile.transform, "Profile result", new Vector2(.5f, .5f), new Vector2(.5f, .5f), Vector2.zero, new Vector2(720f, 300f), 20, TextAnchor.MiddleCenter);
            MakeButton(_profile.transform, "Load profile", "Load profile", new Vector2(-140f, -190f), () => _ = LoadProfileAsync());
            MakeButton(_profile.transform, "Close profile", "Close", new Vector2(140f, -190f), () => ShowProfile(false));
            MakeButton(_menu.transform, "Open journal", "Quest journal", new Vector2(0f, -400f), () => ShowJournal(true));
            _journal = MakePanel(canvasObject.transform, "Quest Journal");
            MakeText(_journal.transform, "Journal title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -56f), new Vector2(700f, 56f), 28, TextAnchor.MiddleCenter).text = "Quest journal • server-authoritative progress";
            _journalText = MakeText(_journal.transform, "Journal entries", new Vector2(.5f, .5f), new Vector2(.5f, .5f), Vector2.zero, new Vector2(720f, 330f), 18, TextAnchor.UpperLeft);
            MakeButton(_journal.transform, "Retry quest events", "Retry pending events", new Vector2(-150f, -230f), _quests.RetryPendingEvents);
            MakeButton(_journal.transform, "Close journal", "Close", new Vector2(150f, -230f), () => ShowJournal(false));
            _dialoguePanel = MakePanel(canvasObject.transform, "Dialogue");
            _dialogueText = MakeText(_dialoguePanel.transform, "Dialogue line", new Vector2(.5f, .68f), new Vector2(.5f, .68f), Vector2.zero, new Vector2(700f, 120f), 22, TextAnchor.MiddleCenter);
            _dialogueChoices = _dialoguePanel.transform;
            MakeButton(_dialoguePanel.transform, "Close dialogue", "Continue / close", new Vector2(0f, -500f), () => AdvanceDialogue());
            _challengePanel = MakePanel(canvasObject.transform, "Coding Challenge");
            _challengeTitle = MakeText(_challengePanel.transform, "Challenge title", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -44f), new Vector2(760f, 54f), 27, TextAnchor.MiddleCenter);
            _challengeTitle.text = "Python challenge";
            _challengeInstructions = MakeText(_challengePanel.transform, "Challenge instructions", new Vector2(.5f, 1f), new Vector2(.5f, 1f), new Vector2(0f, -112f), new Vector2(760f, 110f), 17, TextAnchor.UpperLeft);
            _challengeSource = MakeInputField(_challengePanel.transform, new Vector2(0f, -310f), new Vector2(760f, 220f));
            _challengeFeedback = MakeText(_challengePanel.transform, "Challenge feedback", new Vector2(.5f, 0f), new Vector2(.5f, 0f), new Vector2(0f, 88f), new Vector2(760f, 95f), 16, TextAnchor.MiddleLeft);
            MakeButton(_challengePanel.transform, "Submit challenge", "Submit Python", new Vector2(-270f, -500f), () => _ = SubmitChallengeAsync());
            MakeButton(_challengePanel.transform, "Request hint", "Next hint", new Vector2(0f, -500f), () => _ = RequestChallengeHintAsync());
            MakeButton(_challengePanel.transform, "Return to journal", "Quest journal", new Vector2(270f, -500f), () => ShowJournal(true));
            _catalog.SetActive(false);
            _profile.SetActive(false);
            _journal.SetActive(false);
            _dialoguePanel.SetActive(false);
            _challengePanel.SetActive(false);
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
                foreach (var button in _challengeButtons) UnityEngine.Object.Destroy(button);
                _challengeButtons.Clear();
                for (var index = 0; index < challenges.Value.items.Count && index < 3; index++)
                {
                    var challenge = challenges.Value.items[index];
                    var x = (index - 1) * 270f;
                    _challengeButtons.Add(MakeButton(_catalog.transform, "Open challenge " + challenge.slug,
                        "Practice: " + challenge.title, new Vector2(x, -205f),
                        () => _ = OpenChallengeAsync(challenge.slug, challenge.version)));
                }
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

        private void ShowJournal(bool visible)
        {
            if (visible) RememberModalReturn();
            _challengePanel.SetActive(false);
            _journal.SetActive(visible);
            if (visible)
            {
                _menu.SetActive(false); _catalog.SetActive(false); _profile.SetActive(false);
                _journalText.text = _quests.GetJournalText() + "\n\n" + _quests.PersistenceStatus;
                Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            }
            else RestoreModalReturn();
        }

        private async Task OpenChallengeAsync(string slug, int version)
        {
            BeginRequest();
            var token = _request.Token;
            _activeChallenge = null;
            _activeSubmissionId = null;
            _activeClientSubmissionId = null;
            _activeSubmissionSource = null;
            _nextHintLevel = 1;
            _catalog.SetActive(false);
            _menu.SetActive(false);
            _challengePanel.SetActive(true);
            _challengeInstructions.text = "Loading the published challenge…";
            _challengeFeedback.text = string.Empty;
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
            var result = await _api.GetChallengeAsync(slug, version, token);
            if (!result.IsSuccess)
            {
                _challengeInstructions.text = "Could not load this challenge. " + result.Error.message;
                return;
            }
            _activeChallenge = result.Value;
            _challengeTitle.text = result.Value.title;
            var content = result.Value.publicContent;
            _challengeInstructions.text = result.Value.statement +
                (content == null ? string.Empty : "\n\nSignature: " + content.functionSignature +
                "\n" + content.expectedOutputFormat + "\n\nExamples:\n" + string.Join("\n", content.examples ?? Array.Empty<string>()));
            _challengeSource.text = content == null ? string.Empty : content.starterCode;
        }

        private async Task SubmitChallengeAsync()
        {
            if (_activeChallenge == null) return;
            var source = _challengeSource.text ?? string.Empty;
            if (string.IsNullOrWhiteSpace(source))
            {
                _challengeFeedback.text = "Enter Python code before submitting.";
                return;
            }
            if (source != _activeSubmissionSource)
                _activeClientSubmissionId = Guid.NewGuid().ToString();
            _activeSubmissionSource = source;
            if (string.IsNullOrEmpty(_activeClientSubmissionId))
                _activeClientSubmissionId = Guid.NewGuid().ToString();
            _challengeFeedback.text = "Submitting to the isolated evaluation service…";
            BeginRequest();
            var result = await _api.SubmitChallengeAsync(_activeChallenge.slug,
                new ChallengeSubmissionRequestDto
                {
                    clientSubmissionId = _activeClientSubmissionId,
                    challengeVersion = _activeChallenge.version,
                    source = source
                }, _request.Token);
            if (!result.IsSuccess)
            {
                _challengeFeedback.text = result.Error.message +
                    (result.Error.retryable ? " You can retry; the same request key will be reused." : string.Empty);
                return;
            }
            _activeSubmissionId = result.Value.id;
            _challengeFeedback.text = "Evaluation status: " + result.Value.status;
            await PollSubmissionAsync(_activeSubmissionId, _request.Token);
        }

        private async Task PollSubmissionAsync(string submissionId, CancellationToken token)
        {
            for (var attempt = 0; attempt < 12 && !_lifetime.IsCancellationRequested; attempt++)
            {
                var result = await _api.GetMySubmissionAsync(submissionId, token);
                if (!result.IsSuccess)
                {
                    _challengeFeedback.text = "Could not refresh evaluation status. " + result.Error.message;
                    return;
                }
                var submission = result.Value;
                var status = submission.status ?? "internal_error";
                if (status == "passed" || status == "failed" || status == "timed_out" || status == "internal_error")
                {
                    var evaluation = submission.result;
                    if (evaluation == null || !evaluation.hasResult)
                    {
                        _challengeFeedback.text = status == "timed_out" ? "Evaluation timed out. Try simplifying your approach." :
                            status == "internal_error" ? "The evaluation service failed. No progress or reward was recorded." : status;
                    }
                    else
                    {
                        var detail = status == "passed" ? "Passed" : "Not passed";
                        detail += " • score " + evaluation.scorePercent + "% • " + evaluation.passedTests + "/" + evaluation.totalTests + " tests";
                        if (evaluation.diagnostics != null)
                            foreach (var diagnostic in evaluation.diagnostics) detail += "\n" + diagnostic.message;
                        _challengeFeedback.text = detail;
                    }
                    return;
                }
                _challengeFeedback.text = "Evaluation status: " + status + "…";
                try
                {
                    await Task.Delay(750, token);
                }
                catch (OperationCanceledException)
                {
                    return;
                }
            }
            _challengeFeedback.text = "Evaluation is still pending. Use Submit Python to safely check the same request again.";
        }

        private async Task RequestChallengeHintAsync()
        {
            if (_activeChallenge == null) return;
            BeginRequest();
            var result = await _api.GetChallengeHintAsync(_activeChallenge.slug, _activeChallenge.version,
                _nextHintLevel, _request.Token);
            if (!result.IsSuccess)
            {
                _challengeFeedback.text = result.Error.message;
                return;
            }
            _challengeFeedback.text = "Hint " + result.Value.level + ": " + result.Value.content;
            _nextHintLevel++;
        }

        private void OpenDialogue(DialogueDefinition definition)
        {
            if (!_dialogue.Begin(definition)) return;
            RememberModalReturn();
            _menu.SetActive(false); _catalog.SetActive(false); _profile.SetActive(false); _journal.SetActive(false);
            _dialoguePanel.SetActive(true);
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            RenderDialogue();
        }

        private void AdvanceDialogue()
        {
            var choices = _dialogue.VisibleChoices();
            if (choices.Count == 0) { CloseDialogue(); return; }
            _dialogue.Choose(0);
            RenderDialogue();
        }

        private void RenderDialogue()
        {
            if (_dialogue.Current == null) { CloseDialogue(); return; }
            _dialogueText.text = _dialogue.Current.line;
            foreach (var button in _choiceButtons) UnityEngine.Object.Destroy(button);
            _choiceButtons.Clear();
            var choices = _dialogue.VisibleChoices();
            for (var index = 0; index < choices.Count; index++)
            {
                var choiceIndex = index;
                var y = -310f - index * 56f;
                var button = MakeButton(_dialogueChoices, "Dialogue choice " + index, choices[index].label, new Vector2(0f, y), () =>
                {
                    _dialogue.Choose(choiceIndex);
                    RenderDialogue();
                });
                _choiceButtons.Add(button);
            }
        }

        private void CloseDialogue()
        {
            _dialogue.Cancel(); _dialoguePanel.SetActive(false);
            _interaction.CancelCurrentInteraction();
            RestoreModalReturn();
        }

        private void ShowObjectiveNotification(string description)
        {
            _objectiveNotification.text = "Objective updated: " + description;
            _notificationUntil = Time.unscaledTime + 4f;
        }

        private void OnQuestChanged(QuestProgressSnapshot _)
        {
            if (_journal != null && _journal.activeSelf)
                _journalText.text = _quests.GetJournalText() + "\n\n" + _quests.PersistenceStatus;
        }

        private void RememberModalReturn()
        {
            _returnToMenu = _menu.activeSelf;
            _returnCursorLock = Cursor.lockState;
            _returnCursorVisible = Cursor.visible;
        }

        private void RestoreModalReturn()
        {
            _menu.SetActive(_returnToMenu);
            Cursor.lockState = _returnToMenu ? CursorLockMode.None : CursorLockMode.Locked;
            Cursor.visible = _returnToMenu || _returnCursorVisible && _returnCursorLock != CursorLockMode.Locked;
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

        private static GameObject MakeButton(Transform parent, string name, string label, Vector2 position, Action onClick)
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
            return buttonObject;
        }

        private static InputField MakeInputField(Transform parent, Vector2 position, Vector2 size)
        {
            var inputObject = new GameObject("Python code entry", typeof(RectTransform), typeof(Image), typeof(InputField));
            inputObject.transform.SetParent(parent, false);
            var rect = inputObject.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(.5f, .5f);
            rect.anchorMax = new Vector2(.5f, .5f);
            rect.sizeDelta = size;
            rect.anchoredPosition = position;
            inputObject.GetComponent<Image>().color = new Color(.025f, .035f, .05f, 1f);
            var text = MakeText(inputObject.transform, "Code text", Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero, 16, TextAnchor.UpperLeft);
            text.rectTransform.offsetMin = new Vector2(12f, 10f);
            text.rectTransform.offsetMax = new Vector2(-12f, -10f);
            text.fontStyle = FontStyle.Normal;
            var placeholder = MakeText(inputObject.transform, "Code placeholder", Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero, 15, TextAnchor.UpperLeft);
            placeholder.text = "Write your Python function here…";
            placeholder.color = new Color(.65f, .68f, .72f, 1f);
            placeholder.rectTransform.offsetMin = text.rectTransform.offsetMin;
            placeholder.rectTransform.offsetMax = text.rectTransform.offsetMax;
            var field = inputObject.GetComponent<InputField>();
            field.textComponent = text;
            field.placeholder = placeholder;
            field.lineType = InputField.LineType.MultiLineNewline;
            field.characterLimit = 8192;
            return field;
        }

    }
}
