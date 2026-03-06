# Sudoku

[![OpenReward Environment](https://img.shields.io/badge/%E2%AD%90%20OpenReward-Environment-f7e6cc)](https://openreward.ai/GeneralReasoning/Sudoku)

## Description

**Sudoku** is an environment for evaluating agents on solving Sudoku puzzles of varying difficulty levels. This environment wraps the Sudoku implementation from [TextArena](https://github.com/LeonGuertler/TextArena), a framework for text-based game environments.

## Capabilities

- Solving Sudoku puzzles across five difficulty levels
- Validating logical deduction and constraint satisfaction
- Managing state across multi-turn puzzle completion
- Testing systematic problem-solving approaches

## Compute Requirements

Sudoku does not require a sandbox. It has minimal compute requirements.

## License

[MIT](https://github.com/LeonGuertler/TextArena/blob/main/LICENSE).

## Tasks

There are two splits: train (250 tasks) and test (250 tasks). Each split contains 50 tasks across each of 5 variants:

- **Sudoku-v0-very-easy**
- **Sudoku-v0-easy**
- **Sudoku-v0**
- **Sudoku-v0-medium**
- **Sudoku-v0-hard**

Each task is seeded for reproducibility.

## Reward Structure

This is a sparse reward environment. Rewards are mapped from TextArena's native range of {-1, 0, 1} to {0.0, 0.5, 1.0} via `(raw + 1) / 2`.

We do not use LLM graders for this environment; reward is determined programmatically.

## Data

Game state is generated procedurally by the TextArena engine using seeded randomness. No external data files are required.

## Tools

Agents are given a single tool:

- `place_number(row, column, number)`: Place a number (1-9) at the given row (1-9) and column (1-9) on the Sudoku board.

## Time Horizon

Sudoku is a multi-turn environment.

## Environment Difficulty

Medium to Hard. Sudoku puzzles require logical deduction, constraint satisfaction, and systematic reasoning. Difficulty scales across variants from very-easy to hard.

## Other Environment Requirements

There are no further environment requirements; Sudoku works out of the box without any secrets or API keys.

## Safety

Agents in Sudoku interact only with a logic puzzle and have no access to external systems, the internet, or sensitive data. The environment does not present safety risks.

## Citations

```bibtex
@software{textarena2024,
  author    = {Guertler, Leon and Banting, Wilfried and Pignatelli, Eduardo},
  title     = {TextArena},
  year      = {2024},
  publisher = {GitHub},
  url       = {https://github.com/LeonGuertler/TextArena}
}
```
