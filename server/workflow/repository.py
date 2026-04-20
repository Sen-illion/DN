from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .types import BranchState, GameState, ImageTask, TextNode


class WorkflowRepository(ABC):
    @abstractmethod
    def init_schema(self) -> None: ...

    @abstractmethod
    def save_game_state(self, state: GameState) -> GameState: ...

    @abstractmethod
    def get_game_state(self, game_id: str) -> GameState | None: ...

    @abstractmethod
    def save_text_node(self, node: TextNode) -> TextNode: ...

    @abstractmethod
    def get_text_node(self, game_id: str, text_id: str) -> TextNode | None: ...

    @abstractmethod
    def list_text_nodes(self, game_id: str, branch_id: str | None = None) -> list[TextNode]: ...

    @abstractmethod
    def save_image_task(self, task: ImageTask) -> ImageTask: ...

    @abstractmethod
    def get_image_task(self, game_id: str, anchor_text_id: str) -> ImageTask | None: ...

    @abstractmethod
    def list_image_tasks(self, game_id: str, branch_id: str | None = None) -> list[ImageTask]: ...

    @abstractmethod
    def save_branch_state(self, state: BranchState) -> BranchState: ...

    @abstractmethod
    def get_branch_state(self, game_id: str, branch_id: str) -> BranchState | None: ...

    @abstractmethod
    def list_branch_states(self, game_id: str) -> list[BranchState]: ...

    @abstractmethod
    def append_event(self, game_id: str, event_type: str, payload: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_events(self, game_id: str, event_type: str | None = None) -> list[dict[str, Any]]: ...
