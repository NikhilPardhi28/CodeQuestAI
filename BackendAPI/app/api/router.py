from fastapi import APIRouter

from BackendAPI.app.api import challenges, curriculum, players, quest_events, quests

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(curriculum.router)
api_v1.include_router(quests.router)
api_v1.include_router(challenges.router)
api_v1.include_router(players.router)
api_v2 = quest_events.router
