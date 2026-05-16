from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from src.persistence.database import DatabaseManager


class AgentState:
    def __init__(self, agent_id: str, data: dict[str, Any]) -> None:
        self.agent_id = agent_id
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return {"agent_id": self.agent_id, "data": self.data}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentState:
        return cls(agent_id=d["agent_id"], data=d["data"])


class CheckpointManager:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    async def create_checkpoint(self, agent_id: str, state: AgentState) -> str:
        checkpoint_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        data_json = json.dumps(state.to_dict())
        await self._db.save_checkpoint(checkpoint_id, agent_id, data_json, created_at)
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> AgentState:
        row = await self._db.get_checkpoint(checkpoint_id)
        if row is None:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        data = json.loads(row["data_json"])
        return AgentState.from_dict(data)

    async def list_checkpoints(self, agent_id: str) -> list[dict[str, Any]]:
        return await self._db.list_checkpoints(agent_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        return await self._db.delete_checkpoint(checkpoint_id)
