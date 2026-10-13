using System.Collections;
using System.IO;
using CodeQuest.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UI;

namespace CodeQuest.Tests.PlayMode
{
    public sealed class UiAndCodingPlayModeTests
    {
        [UnityTest]
        public IEnumerator MainMenuButtonsHaveNonEmptyVisibleTextWithValidFont()
        {
            yield return null;
            var menu = GameObject.Find("Main Menu");
            Assert.IsNotNull(menu, "Main Menu panel must exist in the scene.");
            Assert.IsTrue(menu.activeSelf, "Main Menu must be active on startup.");

            var buttons = menu.GetComponentsInChildren<Button>(true);
            Assert.GreaterOrEqual(buttons.Length, 4, "Main Menu must have at least 4 buttons.");

            foreach (var button in buttons)
            {
                var text = button.GetComponentInChildren<Text>();
                Assert.IsNotNull(text, $"Button '{button.gameObject.name}' must have a Text component child.");
                Assert.IsFalse(string.IsNullOrWhiteSpace(text.text), $"Button '{button.gameObject.name}' text must not be empty.");
                Assert.IsNotNull(text.font, $"Button '{button.gameObject.name}' text must have a valid non-null font assigned.");
                Assert.Greater(text.fontSize, 0, $"Button '{button.gameObject.name}' font size must be > 0.");
                Assert.Greater(text.color.a, 0.5f, $"Button '{button.gameObject.name}' text color alpha must be visible (> 0.5).");
                var rect = text.rectTransform.rect;
                Assert.Greater(rect.width, 10f, $"Button '{button.gameObject.name}' text width must be > 10.");
                Assert.Greater(rect.height, 10f, $"Button '{button.gameObject.name}' text height must be > 10.");
            }
        }

        [UnityTest]
        public IEnumerator ChallengePanelMatchesReferenceDesignAndHasEditableInput()
        {
            yield return null;
            GameObject challengePanel = null;
            var panels = Resources.FindObjectsOfTypeAll<GameObject>();
            foreach (var p in panels)
            {
                if (p.name == "Coding Challenge" && p.scene.isLoaded)
                {
                    challengePanel = p;
                    break;
                }
            }
            Assert.IsNotNull(challengePanel, "Coding Challenge panel must exist in the scene hierarchy.");

            var titleObj = challengePanel.transform.Find("Challenge title");
            Assert.IsNotNull(titleObj, "Challenge title must exist.");
            var titleText = titleObj.GetComponent<Text>();
            Assert.IsNotNull(titleText.font, "Title font must not be null.");

            var editorCard = challengePanel.transform.Find("Editor Card");
            Assert.IsNotNull(editorCard, "Editor Card container must exist.");

            var inputField = editorCard.GetComponentInChildren<InputField>(true);
            Assert.IsNotNull(inputField, "Python code InputField must exist in Editor Card.");
            Assert.AreEqual(InputField.LineType.MultiLineNewline, inputField.lineType, "InputField must be MultiLineNewline.");
            Assert.IsNotNull(inputField.textComponent.font, "InputField text font must not be null.");

            // Simulate typing into the InputField
            inputField.text = "message = \"Hello, Valley!\"\nprint(message)";
            yield return null;
            Assert.AreEqual("message = \"Hello, Valley!\"\nprint(message)", inputField.text, "InputField must retain typed Python code.");

            var submitBtn = challengePanel.transform.Find("Submit challenge");
            Assert.IsNotNull(submitBtn, "Submit challenge button must exist.");
            var submitText = submitBtn.GetComponentInChildren<Text>();
            Assert.IsNotNull(submitText, "Submit button text component must exist.");
            Assert.IsTrue(submitText.text.Contains("Run / Submit"), "Submit button must display 'Run / Submit'.");

            var closeBtn = challengePanel.transform.Find("Close challenge");
            Assert.IsNotNull(closeBtn, "Close challenge button must exist.");

            var outputCard = challengePanel.transform.Find("Output Card");
            Assert.IsNotNull(outputCard, "Output Card container must exist.");
            var feedbackText = outputCard.Find("Challenge feedback")?.GetComponent<Text>();
            Assert.IsNotNull(feedbackText, "Challenge feedback text must exist in Output Card.");
            Assert.IsNotNull(feedbackText.font, "Feedback font must not be null.");
        }
    }
}
