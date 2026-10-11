using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using CodeQuest.Gameplay.Dialogue;

namespace CodeQuest.Gameplay.Quests
{
    public enum QuestSyncState { ServerConfirmed, Pending, Failed, LocalOnly }

    [Serializable]
    public sealed class QuestObjectiveServerProgress
    {
        public string objectiveId;
        public int completedCount;
        public int requiredCount;
        public bool completed;
    }

    [Serializable]
    public sealed class QuestProgressSnapshot
    {
        public string questId;
        public int version;
        public QuestStatus status;
        public int revision;
        public QuestSyncState syncState;
        public string lastError;
        public Dictionary<string, int> objectiveCounts = new Dictionary<string, int>();
        public HashSet<string> processedEventIds = new HashSet<string>();
    }

    [Serializable]
    public sealed class QuestEventRequest
    {
        public string eventId;
        public int questVersion;
        public int expectedRevision;
        public string eventType;
        public string targetId;
        public int targetVersion = 1;
        public string challengeSubmissionId;
    }

    [Serializable]
    public sealed class QuestEventServerResult
    {
        public string questSlug;
        public int questVersion;
        public string status;
        public int revision;
        public QuestObjectiveServerProgress[] objectiveProgress;
        public bool replayed;
    }

    public sealed class QuestEventSubmissionResult
    {
        public bool IsSuccess { get; private set; }
        public bool Retryable { get; private set; }
        public string ErrorCode { get; private set; }
        public string ErrorMessage { get; private set; }
        public QuestEventServerResult Value { get; private set; }
        public QuestEventServerResult CurrentState { get; private set; }

        private QuestEventSubmissionResult(bool success, QuestEventServerResult value, QuestEventServerResult currentState,
            string errorCode, string errorMessage, bool retryable)
        {
            IsSuccess = success;
            Value = value;
            CurrentState = currentState;
            ErrorCode = errorCode;
            ErrorMessage = errorMessage;
            Retryable = retryable;
        }

        public static QuestEventSubmissionResult Success(QuestEventServerResult value) =>
            new QuestEventSubmissionResult(true, value, null, null, null, false);
        public static QuestEventSubmissionResult Failure(string code, string message, bool retryable, QuestEventServerResult currentState = null) =>
            new QuestEventSubmissionResult(false, null, currentState, code, message, retryable);
    }

    public sealed class QuestProgressLoadResult
    {
        public bool IsSuccess { get; private set; }
        public IReadOnlyList<QuestEventServerResult> Items { get; private set; }
        public string ErrorMessage { get; private set; }
        public static QuestProgressLoadResult Success(IReadOnlyList<QuestEventServerResult> items) =>
            new QuestProgressLoadResult { IsSuccess = true, Items = items ?? Array.Empty<QuestEventServerResult>() };
        public static QuestProgressLoadResult Failure(string message) =>
            new QuestProgressLoadResult { IsSuccess = false, ErrorMessage = message };
    }

    public interface IQuestProgressPersistence
    {
        bool IsCloudBacked { get; }
        string StatusLabel { get; }
        Task<QuestProgressLoadResult> LoadAsync(CancellationToken cancellationToken);
        Task<QuestEventSubmissionResult> SubmitAsync(string questSlug, QuestEventRequest request, CancellationToken cancellationToken);
    }

    public sealed class LocalOnlyQuestPersistence : IQuestProgressPersistence
    {
        public bool IsCloudBacked => false;
        public string StatusLabel => "Quest progress: local session only • not saved to cloud";
        public Task<QuestProgressLoadResult> LoadAsync(CancellationToken cancellationToken) =>
            Task.FromResult(QuestProgressLoadResult.Failure(StatusLabel));
        public Task<QuestEventSubmissionResult> SubmitAsync(string questSlug, QuestEventRequest request, CancellationToken cancellationToken) =>
            Task.FromResult(QuestEventSubmissionResult.Failure("local_only", StatusLabel, false));
    }

    public sealed class QuestService : IDialogueConditions
    {
        private const int MaxPendingEvents = 32;
        private readonly Dictionary<string, QuestDefinition> _definitions = new Dictionary<string, QuestDefinition>();
        private readonly Dictionary<string, QuestProgressSnapshot> _progress = new Dictionary<string, QuestProgressSnapshot>();
        private readonly List<PendingEvent> _pending = new List<PendingEvent>();
        private readonly IQuestProgressPersistence _persistence;
        private readonly CancellationTokenSource _lifetime = new CancellationTokenSource();
        private bool _loadFinished;
        private bool _loadSucceeded;
        private string _loadError;
        private bool _workerRunning;
        public event Action<QuestProgressSnapshot> Changed;
        public event Action<string> ObjectiveNotification;
        public IReadOnlyCollection<QuestProgressSnapshot> Progress => _progress.Values;
        public string PersistenceStatus => _persistence.StatusLabel;

        public QuestService(IQuestProgressPersistence persistence)
        {
            _persistence = persistence ?? new LocalOnlyQuestPersistence();
            _ = LoadAsync();
        }

        public bool Register(QuestDefinition definition)
        {
            if (definition == null || !definition.IsValid(out _)) return false;
            _definitions[definition.questId] = definition;
            if (!_progress.ContainsKey(definition.questId))
            {
                _progress[definition.questId] = new QuestProgressSnapshot
                {
                    questId = definition.questId,
                    version = definition.version,
                    status = QuestStatus.Available,
                    syncState = !_persistence.IsCloudBacked ? QuestSyncState.LocalOnly :
                        !_loadFinished ? QuestSyncState.Pending : _loadSucceeded ? QuestSyncState.ServerConfirmed : QuestSyncState.Failed,
                    lastError = _loadFinished ? _loadError : null
                };
            }
            Changed?.Invoke(_progress[definition.questId]);
            return true;
        }

        // Activation is a local UI action. It never changes server-confirmed state.
        public bool Activate(string questId) => _definitions.ContainsKey(questId) &&
            _progress.TryGetValue(questId, out var progress) && progress.status != QuestStatus.Completed &&
            PrerequisitesMet(_definitions[questId]);

        // Failure transitions are not part of the server contract.
        public bool Fail(string questId) => false;

        public bool RecordEvent(string questId, string eventId, QuestObjectiveKind kind, string targetId)
        {
            if (!_progress.TryGetValue(questId, out var progress) ||
                !_definitions.TryGetValue(questId, out var definition) ||
                string.IsNullOrWhiteSpace(targetId))
                return false;
            if (_pending.Count >= MaxPendingEvents)
            {
                progress.syncState = QuestSyncState.Failed;
                progress.lastError = "The offline quest event queue is full. Retry or reconnect before continuing.";
                Changed?.Invoke(progress);
                return false;
            }

            var eventType = ToServerEventType(kind);
            var objective = definition.objectives.FirstOrDefault(item => item.kind == kind && item.targetId == targetId);
            if (eventType == null || objective == null)
                return false;
            var id = Guid.TryParse(eventId, out var parsed) ? parsed.ToString("D") : Guid.NewGuid().ToString("D");
            if (!progress.processedEventIds.Add(id)) return false;

            var pending = new PendingEvent(questId, new QuestEventRequest
            {
                eventId = id,
                expectedRevision = -1,
                questVersion = definition.version,
                eventType = eventType,
                targetId = targetId,
                targetVersion = objective.targetVersion
            });
            _pending.Add(pending);
            progress.syncState = QuestSyncState.Pending;
            progress.lastError = null;
            Changed?.Invoke(progress);
            StartWorker();
            return true;
        }

        public void RecordWorldEvent(string eventId, QuestObjectiveKind kind, string targetId)
        {
            foreach (var questId in _definitions.Keys.ToArray()) RecordEvent(questId, eventId, kind, targetId);
        }

        public void RetryPendingEvents()
        {
            foreach (var item in _pending)
            {
                if (_progress.TryGetValue(item.QuestId, out var progress))
                {
                    progress.syncState = QuestSyncState.Pending;
                    progress.lastError = null;
                    Changed?.Invoke(progress);
                }
            }
            StartWorker();
        }

        public bool IsQuestActive(string questId) => _progress.TryGetValue(questId, out var progress) && progress.status == QuestStatus.Active;
        public bool IsQuestCompleted(string questId) => _progress.TryGetValue(questId, out var progress) && progress.status == QuestStatus.Completed && progress.syncState == QuestSyncState.ServerConfirmed;

        public string GetJournalText()
        {
            var lines = new List<string>();
            foreach (var definition in _definitions.Values.OrderBy(item => item.category).ThenBy(item => item.title, StringComparer.Ordinal))
            {
                var progress = _progress[definition.questId];
                lines.Add($"[{progress.status}] {definition.title} (v{definition.version}) — {progress.syncState}");
                if (!string.IsNullOrWhiteSpace(progress.lastError)) lines.Add("  " + progress.lastError);
                if (progress.status == QuestStatus.Active)
                    foreach (var objective in definition.objectives)
                    {
                        progress.objectiveCounts.TryGetValue(objective.id, out var count);
                        lines.Add($"  {count}/{objective.targetCount} {objective.description}");
                    }
            }
            return string.Join("\n", lines);
        }

        private async Task LoadAsync()
        {
            try
            {
                var result = await _persistence.LoadAsync(_lifetime.Token);
                if (result.IsSuccess)
                {
                    _loadSucceeded = true;
                    foreach (var serverProgress in result.Items)
                        if (serverProgress != null && _progress.TryGetValue(serverProgress.questSlug, out var local) &&
                            local.version == serverProgress.questVersion)
                            ApplyServerState(local, serverProgress);
                    foreach (var local in _progress.Values)
                        if (local.syncState != QuestSyncState.ServerConfirmed)
                            local.syncState = QuestSyncState.ServerConfirmed;
                }
                else
                {
                    _loadError = result.ErrorMessage;
                    foreach (var local in _progress.Values)
                    {
                        local.syncState = _persistence.IsCloudBacked ? QuestSyncState.Failed : QuestSyncState.LocalOnly;
                        local.lastError = result.ErrorMessage;
                    }
                }
            }
            catch (Exception exception)
            {
                _loadError = exception.Message;
                SetAllFailed(exception.Message);
            }
            finally
            {
                _loadFinished = true;
                foreach (var progress in _progress.Values) Changed?.Invoke(progress);
                StartWorker();
            }
        }

        private void StartWorker()
        {
            if (!_loadFinished || _workerRunning || _pending.Count == 0) return;
            _ = SubmitPendingAsync();
        }

        private async Task SubmitPendingAsync()
        {
            _workerRunning = true;
            try
            {
                while (_pending.Count > 0)
                {
                    var item = _pending[0];
                    if (!_progress.TryGetValue(item.QuestId, out var progress)) { _pending.RemoveAt(0); continue; }
                    if (item.Request.expectedRevision < 0) item.Request.expectedRevision = progress.revision;
                    if (!_persistence.IsCloudBacked)
                    {
                        progress.syncState = QuestSyncState.LocalOnly;
                        progress.lastError = _persistence.StatusLabel;
                        Changed?.Invoke(progress);
                        break;
                    }
                    var result = await _persistence.SubmitAsync(item.QuestId, item.Request, _lifetime.Token);
                    if (!result.IsSuccess)
                    {
                        if (result.CurrentState != null && result.ErrorCode == "quest_revision_conflict")
                        {
                            ApplyServerState(progress, result.CurrentState);
                            item.Request.expectedRevision = progress.revision;
                        }
                        progress.syncState = QuestSyncState.Failed;
                        progress.lastError = result.ErrorMessage;
                        Changed?.Invoke(progress);
                        break;
                    }
                    ApplyServerState(progress, result.Value);
                    _pending.RemoveAt(0);
                    progress.syncState = HasPending(progress.questId) ? QuestSyncState.Pending : QuestSyncState.ServerConfirmed;
                    progress.lastError = null;
                    Changed?.Invoke(progress);
                    if (result.Value.objectiveProgress != null)
                        foreach (var objective in result.Value.objectiveProgress.Where(item => item.completed))
                        {
                            var authored = _definitions[progress.questId].objectives.FirstOrDefault(item => item.id == objective.objectiveId);
                            if (authored != null) ObjectiveNotification?.Invoke(authored.description);
                        }
                }
            }
            catch (OperationCanceledException) { }
            catch (Exception exception)
            {
                if (_pending.Count > 0 && _progress.TryGetValue(_pending[0].QuestId, out var progress))
                {
                    progress.syncState = QuestSyncState.Failed;
                    progress.lastError = exception.Message;
                    Changed?.Invoke(progress);
                }
            }
            finally
            {
                _workerRunning = false;
            }
        }

        private void ApplyServerState(QuestProgressSnapshot local, QuestEventServerResult server)
        {
            local.version = server.questVersion;
            local.revision = server.revision;
            local.status = ParseStatus(server.status);
            local.objectiveCounts.Clear();
            foreach (var objective in server.objectiveProgress ?? Array.Empty<QuestObjectiveServerProgress>())
                local.objectiveCounts[objective.objectiveId] = objective.completedCount;
            local.syncState = QuestSyncState.ServerConfirmed;
        }

        private void SetAllFailed(string message)
        {
            foreach (var progress in _progress.Values)
            {
                progress.syncState = _persistence.IsCloudBacked ? QuestSyncState.Failed : QuestSyncState.LocalOnly;
                progress.lastError = message;
            }
        }

        private bool HasPending(string questId) => _pending.Any(item => item.QuestId == questId);
        private bool PrerequisitesMet(QuestDefinition definition) => definition.prerequisites == null || definition.prerequisites.All(IsQuestCompleted);
        private static QuestStatus ParseStatus(string status) => status switch
        {
            "in_progress" => QuestStatus.Active,
            "completed" => QuestStatus.Completed,
            "locked" => QuestStatus.Locked,
            "abandoned" => QuestStatus.Failed,
            _ => QuestStatus.Available
        };
        private static string ToServerEventType(QuestObjectiveKind kind) => kind switch
        {
            QuestObjectiveKind.Interact => "interact",
            QuestObjectiveKind.Checkpoint => "checkpoint",
            QuestObjectiveKind.ChallengePassed => "challenge_passed",
            _ => null
        };

        private sealed class PendingEvent
        {
            public string QuestId { get; }
            public QuestEventRequest Request { get; }
            public PendingEvent(string questId, QuestEventRequest request) { QuestId = questId; Request = request; }
        }
    }
}
