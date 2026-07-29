import textarena as ta
import re
from typing import List
from pydantic import BaseModel, field_validator
from openreward.environments import Environment, JSONObject, ToolOutput, TextBlock, tool


class TaskSpec(BaseModel):
    id: str
    env_id: str
    seed: int
    variant: str = ""


class PlaceNumberParams(BaseModel, extra="forbid"):
    row: int
    column: int
    number: int

    @field_validator("row", "column", "number")
    @classmethod
    def validate_range(cls, v):
        if not 1 <= v <= 9:
            raise ValueError("Must be between 1 and 9")
        return v


class SudokuEnvironment(Environment):
    GAME_NAME = "Sudoku"
    VARIANTS = [
        "Sudoku-v0-very-easy",
        "Sudoku-v0-easy",
        "Sudoku-v0",
        "Sudoku-v0-medium",
        "Sudoku-v0-hard",
    ]
    NUM_TASKS_PER_VARIANT = 50

    def __init__(self, task_spec: JSONObject, secrets: dict[str, str] = {}) -> None:
        super().__init__(task_spec)
        self.config = TaskSpec.model_validate(task_spec)
        self.ta_env = ta.make(env_id=self.config.env_id)
        self.game_done = False
        self.turn_count = 0

    @classmethod
    def list_splits(cls) -> list[str]:
        return ["train", "test"]

    @classmethod
    def list_tasks(cls, split: str) -> list[JSONObject]:
        tasks = []
        for variant_id in cls.VARIANTS:
            for seed_idx in range(cls.NUM_TASKS_PER_VARIANT):
                seed = seed_idx if split == "train" else seed_idx + 10000
                tasks.append({
                    "id": f"{variant_id}_seed{seed}",
                    "env_id": variant_id,
                    "seed": seed,
                    "variant": variant_id,
                })
        return tasks

    def _format_observation(self, observation) -> str:
        if isinstance(observation, str):
            match = None
            for m in re.finditer(r'^\[(?!GAME\])[^\]]+\].*$', observation, re.MULTILINE):
                match = m
            if match:
                return observation[match.end():].lstrip('\n')
            return observation
        if isinstance(observation, list):
            if not observation:
                return ""
            last = observation[-1]
            if isinstance(last, tuple) and len(last) >= 2:
                return str(last[1])
            return str(last)
        return str(observation)

    async def get_prompt(self) -> List[TextBlock]:
        self.ta_env.reset(num_players=1, seed=self.config.seed)
        _, observation = self.ta_env.get_observation()
        obs_text = self._format_observation(observation)
        prompt = (
            f"You are playing Sudoku.\n\n"
            f"{obs_text}\n\n"
            f"Use the place_number tool to fill in cells.\n"
            f"Parameters: row (1-9), column (1-9), number (1-9).\n"
            f"Each row, column, and 3x3 box must contain digits 1-9 exactly once."
        )
        return [TextBlock(text=prompt)]

    @tool
    async def place_number(self, params: PlaceNumberParams) -> ToolOutput:
        """Place a number (1-9) at the given row (1-9) and column (1-9) on the Sudoku board."""
        if self.game_done:
            return ToolOutput(
                blocks=[TextBlock(text="Game is already over.")],
                metadata={"error": "game_finished"},
                reward=0.0,
                finished=True,
            )

        action = f"[{params.row} {params.column} {params.number}]"
        done, info = self.ta_env.step(action=action)
        self.turn_count += 1

        if done:
            self.game_done = True
            rewards, game_info = self.ta_env.close()
            # TextArena's Sudoku already returns a reward in [0, 1] (1.0 on a
            # completed puzzle, otherwise the fraction of empty cells correctly
            # filled), so pass it through unchanged rather than remapping an
            # already-normalised value through (raw + 1) / 2, which compressed
            # every outcome into [0.5, 1.0] and paid a zero-progress attempt 0.5.
            reward = rewards.get(0, 0.0) if isinstance(rewards, dict) else float(rewards)
            reason = ""
            if isinstance(game_info, dict) and 0 in game_info:
                reason = game_info[0].get("reason", "")
            summary = f"Game Over! Reward: {reward:.2f}"
            if reason:
                summary += f"\n{reason}"
            return ToolOutput(
                blocks=[TextBlock(text=summary)],
                metadata={"turn": self.turn_count, "reward": reward},
                reward=reward,
                finished=True,
            )

        _, observation = self.ta_env.get_observation()
        obs_text = self._format_observation(observation)
        return ToolOutput(
            blocks=[TextBlock(text=obs_text)],
            metadata={"turn": self.turn_count},
            reward=0.0,
            finished=False,
        )
