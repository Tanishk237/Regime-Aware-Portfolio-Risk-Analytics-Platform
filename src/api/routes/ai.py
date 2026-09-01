from __future__ import annotations

from fastapi import APIRouter, Depends

from src.ai import CopilotAIService
from src.api.dependencies import get_current_user
from src.api.schemas_ai import CopilotChatRequest, CopilotChatResponse
from src.database.models import User


router = APIRouter(prefix="/ai")


@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    payload: CopilotChatRequest,
    user: User = Depends(get_current_user),
) -> CopilotChatResponse:
    result = await CopilotAIService().generate(
        provider=payload.provider,
        api_key=payload.api_key,
        prompt=payload.prompt,
        context={
            **payload.context,
            "user": {
                "id": user.id,
                "email": user.email,
            },
        },
        history=[message.model_dump() for message in payload.history],
        model=payload.model,
    )
    return CopilotChatResponse(**result)
