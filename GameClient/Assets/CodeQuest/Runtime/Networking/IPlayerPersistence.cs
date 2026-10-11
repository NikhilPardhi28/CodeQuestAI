using System.Threading;
using System.Threading.Tasks;
using CodeQuest.Gameplay.Quests;

namespace CodeQuest.Networking
{
    /// <summary>Account-scoped reads plus the versioned, server-authoritative quest event contract.</summary>
    public interface IPlayerPersistence : IQuestProgressPersistence
    {
        bool CanWriteQuestProgress { get; }
        Task<ApiResult<PlayerProfileDto>> GetMyProfileAsync(CancellationToken cancellationToken);
        Task<ApiResult<PlayerProfileDto>> SaveMyProfileAsync(PlayerProfileUpsertDto profile, CancellationToken cancellationToken);
        Task<ApiResult<ProgressionDto>> GetMyProgressionAsync(CancellationToken cancellationToken);
        Task<ApiResult<PageDto<QuestProgressDto>>> GetMyQuestProgressAsync(CancellationToken cancellationToken);
    }
}
