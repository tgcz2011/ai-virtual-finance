from __future__ import annotations

import os
import tempfile

import pytest
import pytest_asyncio

from src.persistence.checkpoint import AgentState, CheckpointManager
from src.persistence.database import DatabaseManager


@pytest_asyncio.fixture
async def checkpoint_manager():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = DatabaseManager(path)
    await db.initialize()
    manager = CheckpointManager(db)
    yield manager
    await db.close()
    if os.path.exists(path):
        os.remove(path)


class TestCheckpointManager:
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        state = AgentState(agent_id="agent-1", data={"cash": 10000.0, "positions": {}})
        cp_id = await checkpoint_manager.create_checkpoint("agent-1", state)
        assert isinstance(cp_id, str)
        assert len(cp_id) > 0

    @pytest.mark.asyncio
    async def test_restore_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        state = AgentState(agent_id="agent-1", data={"cash": 10000.0, "positions": {"AAPL": 10}})
        cp_id = await checkpoint_manager.create_checkpoint("agent-1", state)
        restored = await checkpoint_manager.restore_checkpoint(cp_id)
        assert restored.agent_id == "agent-1"
        assert restored.data["cash"] == 10000.0
        assert restored.data["positions"]["AAPL"] == 10

    @pytest.mark.asyncio
    async def test_restore_nonexistent_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        with pytest.raises(ValueError, match="not found"):
            await checkpoint_manager.restore_checkpoint("missing-id")

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, checkpoint_manager: CheckpointManager) -> None:
        state1 = AgentState(agent_id="agent-1", data={"version": 1})
        state2 = AgentState(agent_id="agent-1", data={"version": 2})
        await checkpoint_manager.create_checkpoint("agent-1", state1)
        await checkpoint_manager.create_checkpoint("agent-1", state2)
        cps = await checkpoint_manager.list_checkpoints("agent-1")
        assert len(cps) == 2
        for cp in cps:
            assert "id" in cp
            assert "agent_id" in cp
            assert "data_json" in cp
            assert "created_at" in cp

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty(self, checkpoint_manager: CheckpointManager) -> None:
        cps = await checkpoint_manager.list_checkpoints("agent-no-cp")
        assert cps == []

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        state = AgentState(agent_id="agent-1", data={})
        cp_id = await checkpoint_manager.create_checkpoint("agent-1", state)
        result = await checkpoint_manager.delete_checkpoint(cp_id)
        assert result is True
        with pytest.raises(ValueError, match="not found"):
            await checkpoint_manager.restore_checkpoint(cp_id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_checkpoint(self, checkpoint_manager: CheckpointManager) -> None:
        result = await checkpoint_manager.delete_checkpoint("missing-id")
        assert result is False
