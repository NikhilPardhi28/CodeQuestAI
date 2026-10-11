using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using CodeQuest.Gameplay.Challenges;
using CodeQuest.Gameplay.Dialogue;
using CodeQuest.Gameplay.Quests;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace CodeQuest.Tests.EditMode
{
    public sealed class GameplayFoundationTests
    {
        [Test]
        public void DialogueChoicesRespectQuestConditionsAndCancelSafely()
        {
            var definition = ScriptableObject.CreateInstance<DialogueDefinition>();
            definition.entryNodeId = "start";
            definition.nodes = new[]
            {
                new DialogueNode { id = "start", line = "Choose", choices = new[] {
                    new DialogueChoice { label = "Always", nextNodeId = "end" },
                    new DialogueChoice { label = "Start quest", nextNodeId = "end", condition = DialogueConditionKind.QuestNotStarted, questId = "q" },
                    new DialogueChoice { label = "After quest", nextNodeId = "end", condition = DialogueConditionKind.QuestCompleted, questId = "q" }
                }},
                new DialogueNode { id = "end", line = "Done" }
            };
            var session = new DialogueSession(new Conditions(false));
            Assert.IsTrue(session.Begin(definition));
            Assert.AreEqual(2, session.VisibleChoices().Count);
            Assert.IsTrue(session.Choose(0));
            Assert.AreEqual("Done", session.Current.line);
            session.Cancel();
            Assert.IsFalse(session.IsOpen);
            Object.DestroyImmediate(definition);
        }

        [Test]
        public void RuleBasedTutorRevealsHintsProgressivelyAndUsesErrorCategory()
        {
            var tutor = new RuleBasedTutorHintProvider();
            var hints = new[] { "Store the input.", "Combine the values.", "Return the result." };
            var first = tutor.GetHint(new TutorHintContext { PublishedHints = hints, HintLevel = 1 });
            var second = tutor.GetHint(new TutorHintContext { PublishedHints = hints, HintLevel = 2 });
            var afterError = tutor.GetHint(new TutorHintContext
            {
                PublishedHints = hints,
                HintLevel = 1,
                LastError = ChallengeErrorCategory.WrongAnswer
            });
            Assert.AreEqual("Store the input.", first);
            Assert.AreEqual("Combine the values.", second);
            StringAssert.Contains("Compare the required output", afterError);
            StringAssert.Contains("Store the input.", afterError);
        }

        [Test]
        public void LocalEditorCheckValidatesOnlyExpectedHeader()
        {
            Assert.IsTrue(ChallengeEditorRules.HasExpectedFunctionHeader("# lesson\ndef make_name_tag(name):\n    pass", "make_name_tag"));
            Assert.IsFalse(ChallengeEditorRules.HasExpectedFunctionHeader("def other(name): return name", "make_name_tag"));
            Assert.IsFalse(ChallengeEditorRules.HasExpectedFunctionHeader("", "make_name_tag"));
        }

        [Test]
        public void ChallengeLifecycleOnlyTreatsServerPassedAsConfirmed()
        {
            Assert.AreEqual(SubmissionStatus.Queued, ChallengeStatusRules.FromServer("queued"));
            Assert.AreEqual(SubmissionStatus.Running, ChallengeStatusRules.FromServer("running"));
            Assert.AreEqual(SubmissionStatus.TimedOut, ChallengeStatusRules.FromServer("timed_out"));
            Assert.AreEqual(SubmissionStatus.InternalError, ChallengeStatusRules.FromServer("unknown"));
            Assert.IsTrue(ChallengeStatusRules.IsConfirmedPass(ChallengeStatusRules.FromServer("passed")));
            Assert.IsFalse(ChallengeStatusRules.IsConfirmedPass(ChallengeStatusRules.FromServer("failed")));
        }

        [Test]
        public void RegisterAfterProgressLoadRestoresMatchingServerRevision()
        {
            var persistence = new ConfirmingPersistence
            {
                LoadedItems = new List<QuestEventServerResult>
                {
                    new QuestEventServerResult
                    {
                        questSlug = "restored", questVersion = 1, status = "in_progress", revision = 4,
                        objectiveProgress = new[] { new QuestObjectiveServerProgress { objectiveId = "a", completedCount = 1, requiredCount = 1, completed = true } }
                    }
                }
            };
            var service = new QuestService(persistence);
            var quest = CreateQuest("restored", null, "a", QuestObjectiveKind.Interact, "switch", 1);
            service.Register(quest);
            var restored = service.Progress.Single();
            Assert.AreEqual(4, restored.revision);
            Assert.AreEqual(QuestStatus.Active, restored.status);
            Assert.AreEqual(QuestSyncState.ServerConfirmed, restored.syncState);
            Assert.IsTrue(restored.objectiveCounts.ContainsKey("a"));
            Object.DestroyImmediate(quest);
        }

        [Test]
        public void QuestProgressChangesOnlyAfterServerConfirmation()
        {
            var persistence = new ConfirmingPersistence();
            var service = new QuestService(persistence);
            var first = CreateQuest("first", null, "a", QuestObjectiveKind.Interact, "switch", 1);
            var second = CreateQuest("second", new[] { "first" }, "b", QuestObjectiveKind.DialogueEvent, "keeper", 1);
            Assert.IsTrue(service.Register(first));
            Assert.IsTrue(service.Register(second));
            Assert.IsFalse(service.Activate("second"));
            Assert.IsTrue(service.Activate("first"));
            Assert.IsTrue(service.RecordEvent("first", "one", QuestObjectiveKind.Interact, "switch"));
            Assert.IsTrue(service.IsQuestCompleted("first"));
            Assert.IsFalse(service.RecordEvent("second", "three", QuestObjectiveKind.DialogueEvent, "keeper"));
            Assert.AreEqual(QuestSyncState.ServerConfirmed, service.Progress.Single(item => item.questId == "first").syncState);
            Object.DestroyImmediate(first);
            Object.DestroyImmediate(second);
        }

        [Test]
        public void LocalOnlyEventsNeverAppearServerConfirmed()
        {
            var service = new QuestService(new LocalOnlyQuestPersistence());
            var quest = CreateQuest("local", null, "a", QuestObjectiveKind.Interact, "switch", 1);
            Assert.IsTrue(service.Register(quest));
            Assert.IsTrue(service.RecordEvent("local", "one", QuestObjectiveKind.Interact, "switch"));
            Assert.AreNotEqual(QuestStatus.Completed, service.Progress.Single().status);
            Assert.AreEqual(QuestSyncState.LocalOnly, service.Progress.Single().syncState);
            StringAssert.Contains("not saved to cloud", service.PersistenceStatus);
            Object.DestroyImmediate(quest);
        }

        [Test]
        public void FailedEventCanBeRetriedWithTheSameIdempotencyKey()
        {
            var persistence = new ConfirmingPersistence
            {
                FirstFailure = QuestEventSubmissionResult.Failure("service_unavailable", "offline", true)
            };
            var service = new QuestService(persistence);
            var quest = CreateQuest("retry", null, "a", QuestObjectiveKind.Interact, "switch", 1);
            service.Register(quest);
            var eventId = System.Guid.NewGuid().ToString();
            Assert.IsTrue(service.RecordEvent("retry", eventId, QuestObjectiveKind.Interact, "switch"));
            Assert.AreEqual(QuestSyncState.Failed, service.Progress.Single().syncState);
            service.RetryPendingEvents();
            Assert.AreEqual(QuestSyncState.ServerConfirmed, service.Progress.Single().syncState);
            Assert.AreEqual(2, persistence.SubmittedIds.Count);
            Assert.AreEqual(persistence.SubmittedIds[0], persistence.SubmittedIds[1]);
            Object.DestroyImmediate(quest);
        }

        [UnityTest]
        public IEnumerator QuestEventRemainsPendingUntilBackendConfirmation()
        {
            var persistence = new ConfirmingPersistence
            {
                DeferredSubmission = new TaskCompletionSource<QuestEventSubmissionResult>()
            };
            var service = new QuestService(persistence);
            var quest = CreateQuest("pending", null, "a", QuestObjectiveKind.Interact, "switch", 1);
            service.Register(quest);
            Assert.IsTrue(service.RecordEvent("pending", "event", QuestObjectiveKind.Interact, "switch"));
            Assert.AreEqual(QuestSyncState.Pending, service.Progress.Single().syncState);
            Assert.AreNotEqual(QuestStatus.Completed, service.Progress.Single().status);

            persistence.DeferredSubmission.SetResult(QuestEventSubmissionResult.Success(new QuestEventServerResult
            {
                questSlug = "pending",
                questVersion = 1,
                status = "completed",
                revision = 1,
                objectiveProgress = new[] { new QuestObjectiveServerProgress { objectiveId = "a", completedCount = 1, requiredCount = 1, completed = true } }
            }));
            yield return null;
            yield return null;

            Assert.AreEqual(QuestSyncState.ServerConfirmed, service.Progress.Single().syncState);
            Assert.AreEqual(QuestStatus.Completed, service.Progress.Single().status);
            Object.DestroyImmediate(quest);
        }

        private static QuestDefinition CreateQuest(string id, string[] prerequisites, string objectiveId, QuestObjectiveKind kind, string target, int count)
        {
            var quest = ScriptableObject.CreateInstance<QuestDefinition>();
            quest.questId = id;
            quest.version = 1;
            quest.title = id;
            quest.prerequisites = prerequisites;
            quest.objectives = new[] { new QuestObjectiveDefinition { id = objectiveId, description = target, kind = kind, targetId = target, targetCount = count } };
            return quest;
        }

        private sealed class Conditions : IDialogueConditions
        {
            private readonly bool _completed;
            public Conditions(bool completed) => _completed = completed;
            public bool IsQuestActive(string questId) => false;
            public bool IsQuestCompleted(string questId) => _completed;
            public bool IsQuestStarted(string questId) => _completed;
        }

        private sealed class ConfirmingPersistence : IQuestProgressPersistence
        {
            public bool IsCloudBacked => true;
            public string StatusLabel => "server authoritative";
            public QuestEventSubmissionResult FirstFailure;
            public TaskCompletionSource<QuestEventSubmissionResult> DeferredSubmission;
            public List<QuestEventServerResult> LoadedItems = new List<QuestEventServerResult>();
            public readonly List<string> SubmittedIds = new List<string>();
            public Task<QuestProgressLoadResult> LoadAsync(CancellationToken cancellationToken) =>
                Task.FromResult(QuestProgressLoadResult.Success(LoadedItems));
            public Task<QuestEventSubmissionResult> SubmitAsync(string questSlug, QuestEventRequest request, CancellationToken cancellationToken)
            {
                SubmittedIds.Add(request.eventId);
                if (DeferredSubmission != null) return DeferredSubmission.Task;
                if (FirstFailure != null)
                {
                    var failure = FirstFailure;
                    FirstFailure = null;
                    return Task.FromResult(failure);
                }
                return Task.FromResult(QuestEventSubmissionResult.Success(new QuestEventServerResult
                {
                    questSlug = questSlug,
                    questVersion = request.questVersion,
                    status = "completed",
                    revision = request.expectedRevision + 1,
                    objectiveProgress = new[] { new QuestObjectiveServerProgress { objectiveId = "a", completedCount = 1, requiredCount = 1, completed = true } }
                }));
            }
        }
    }
}
