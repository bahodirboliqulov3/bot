import asyncio
import json
import logging
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from app.config import settings

logger = logging.getLogger("fsm_storage")


@dataclass
class StorageRecord:
    state: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)


class PersistentFSMStorage(BaseStorage):
    """
    High-performance, persistent FSM storage for Aiogram 3.
    Keeps state in-memory for 0-latency access and automatically
    persists to disk asynchronously so states survive bot restarts.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or (settings.DATA_DIR / "fsm_storage.json")
        self.storage: defaultdict[StorageKey, StorageRecord] = defaultdict(StorageRecord)
        self._dirty = False
        self._load_from_disk()

    def _load_from_disk(self):
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for k_str, rec in raw_data.items():
                        parts = k_str.split(":")
                        if len(parts) == 5:
                            bot_id, chat_id, user_id, thread_id, dest = parts
                            key = StorageKey(
                                bot_id=int(bot_id),
                                chat_id=int(chat_id) if chat_id != "None" else None,
                                user_id=int(user_id) if user_id != "None" else None,
                                thread_id=int(thread_id) if thread_id != "None" else None,
                                destiny=dest if dest != "None" else "default"
                            )
                            self.storage[key] = StorageRecord(
                                state=rec.get("state"),
                                data=rec.get("data", {})
                            )
                logger.info("Loaded %d persistent FSM states from %s", len(self.storage), self.file_path)
        except Exception as e:
            logger.warning("Could not load FSM state from disk: %s", e)

    def _save_to_disk(self):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for key, rec in self.storage.items():
                if rec.state or rec.data:
                    k_str = f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id}:{key.destiny}"
                    serializable[k_str] = {
                        "state": rec.state,
                        "data": rec.data
                    }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            self._dirty = False
        except Exception as e:
            logger.warning("Could not save FSM state to disk: %s", e)

    async def close(self) -> None:
        self._save_to_disk()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        self.storage[key].state = state.state if isinstance(state, State) else state
        self._save_to_disk()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        return self.storage[key].state

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        self.storage[key].data = dict(data)
        self._save_to_disk()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        return self.storage[key].data.copy()

    async def get_value(
        self,
        storage_key: StorageKey,
        dict_key: str,
        default: Optional[Any] = None,
    ) -> Optional[Any]:
        data = self.storage[storage_key].data
        return copy(data.get(dict_key, default))
