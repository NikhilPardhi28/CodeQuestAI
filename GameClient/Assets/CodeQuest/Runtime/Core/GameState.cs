namespace CodeQuest.Core
{
    public enum GameState
    {
        Booting,
        MainMenu,
        Loading,
        InWorld,
        RecoverableError
    }

    public interface IGameStateService
    {
        GameState Current { get; }
        void ChangeTo(GameState next);
    }

    public interface IPlayerState
    {
        string PlayerId { get; }
        int Level { get; }
        int Experience { get; }
        int CurrentHealth { get; }
        int MaximumHealth { get; }
    }

    public sealed class GameStateService : IGameStateService
    {
        public GameState Current { get; private set; } = GameState.Booting;
        public event System.Action<GameState> Changed;

        public void ChangeTo(GameState next)
        {
            if (Current == next) return;
            Current = next;
            Changed?.Invoke(next);
        }
    }
}
