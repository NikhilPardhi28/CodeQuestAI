using CodeQuest.Gameplay.Player;
using CodeQuest.Networking;
using NUnit.Framework;
using UnityEngine;

namespace CodeQuest.Tests.EditMode
{
    public sealed class ContractAndMovementTests
    {
        [Test]
        public void PageAndRegionJsonDeserializeFromBackendCamelCaseContract()
        {
            const string json = "{\"items\":[{\"slug\":\"variable-vale\",\"version\":1,\"name\":\"Variable Vale\",\"summary\":\"Learn values.\",\"sortOrder\":1,\"unlockRegionSlug\":null}],\"limit\":20,\"offset\":0,\"total\":1}";
            var page = JsonUtility.FromJson<PageDto<RegionDto>>(json);
            Assert.AreEqual(1, page.total);
            Assert.AreEqual("variable-vale", page.items[0].slug);
            Assert.IsTrue(string.IsNullOrEmpty(page.items[0].unlockRegionSlug));
        }

        [Test]
        public void ChallengeContentUsesOnlyPublicContractFields()
        {
            const string json = "{\"slug\":\"signal-coordinate\",\"version\":1,\"objectiveSlug\":\"variables-and-assignment\",\"objectiveVersion\":1,\"title\":\"Signal Coordinate\",\"statement\":\"Print a pair.\",\"publicContent\":{\"examples\":[],\"visibleHints\":[\"Name values.\"]}}";
            var challenge = JsonUtility.FromJson<ChallengeDto>(json);
            Assert.AreEqual("signal-coordinate", challenge.slug);
            Assert.AreEqual("Name values.", challenge.publicContent.visibleHints[0]);
        }

        [Test]
        public void MovementRulesClampDiagonalAndChooseRunSpeed()
        {
            var clamped = MovementRules.ClampInput(new Vector2(1f, 1f));
            Assert.That(clamped.magnitude, Is.EqualTo(1f).Within(0.0001f));
            Assert.AreEqual(4f, MovementRules.SelectSpeed(false, 4f, 6.5f));
            Assert.AreEqual(6.5f, MovementRules.SelectSpeed(true, 4f, 6.5f));
            Assert.Greater(MovementRules.JumpVelocity(1f, 20f), 0f);
        }
    }
}
