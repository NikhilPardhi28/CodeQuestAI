# Milestone 5 gameplay foundation

## Implemented

- `CodeQuest.Gameplay` owns reusable interaction, dialogue, quest, and challenge boundaries. `PlayerInteractor` selects the closest target, then higher selection priority, then ordinal interaction ID; unavailable targets keep a visible reason. Interaction lifecycle events and explicit cancellation are exposed.
- `InteractableBehaviour` is a reusable component base. Door, switch, checkpoint, chest, and NPC dialogue examples use the same detector. The Bootstrap greybox includes a signal keeper, branching dialogue, and relay-switch quest.
- Dialogue is authored as `DialogueDefinition` ScriptableObjects and supports quest-active/completed choice conditions and events. The runtime dialogue view supports choices, Escape cancellation, and cursor/UI lifecycle.
- Versioned `QuestDefinition` assets declare categories, prerequisites, objectives, and reward metadata. `QuestService` handles activation, failure, objective counts, prerequisite gating, duplicate event IDs, completion, and journal text. Rewards are definitions only; completion does not grant them.
- `IPlayerPersistence` exposes authenticated profile read/upsert and progression/quest snapshot reads from existing API v1 routes. Quest writes are explicitly unsupported. The quest journal labels the current implementation as local-session-only. The checkpoint and chest examples make no cloud-save or persistent-reward claim.
- `IChallengeSubmissionService` defines version-pinned challenge references, submission lifecycle, evaluation summaries, hints, and objective context. No implementation executes source code.

## Persistence and authority

At the end of Milestone 5, quest state was local-only and the API had no quest mutation contract. Milestone 6 preserves the reusable gameplay foundation while replacing quest mutation with server-submitted v2 events. Only registered interaction, checkpoint, challenge-pass, and prerequisite events can advance versioned server rules; dialogue signals are not treated as authoritative quest events. See the [implemented v2 contract](api/README.md#quest-events-v2-contract-milestone-6). Persistent rewards/progression are computed from server-validated rules, never client-provided claims.

Profile initialization uses the existing OIDC identity boundary. This milestone does not add a fake local identity, store credentials, or change authentication. Python execution remains behind a future isolated worker interface.

## Verification

Focused Unity tests cover dialogue branch filtering/cancellation, prerequisite and objective transitions, duplicate events, local persistence labeling, deterministic target selection, unavailable prompts, and the existing runtime foundation. Actual test results belong in the completion report for the run that executes them; this document does not imply they passed.
