import pytest

from env import PlaceNumberParams, SudokuEnvironment

TASKS = SudokuEnvironment.list_tasks("train")
ONE_PER_VARIANT = [TASKS[i * SudokuEnvironment.NUM_TASKS_PER_VARIANT] for i in range(len(SudokuEnvironment.VARIANTS))]


async def new_env(task):
    env = SudokuEnvironment(task_spec=task)
    await env.get_prompt()
    return env


def empty_cells(env):
    """(row, col, solution, wrong_digit) for every empty cell, 1-based."""
    cells = []
    for i in range(9):
        for j in range(9):
            if env.ta_env.game_board[i][j] == 0:
                sol = env.ta_env.full_grid[i][j]
                cells.append((i + 1, j + 1, sol, sol % 9 + 1))
    return cells


async def place(env, row, col, num):
    return await env.place_number(PlaceNumberParams(row=row, column=col, number=num))


async def fill_correct(env, cells):
    outs = []
    for r, c, sol, _ in cells:
        outs.append(await place(env, r, c, sol))
    return outs


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ONE_PER_VARIANT, ids=lambda t: t["id"])
async def test_gold_win_totals_exactly_one(task):
    env = await new_env(task)
    cells = empty_cells(env)
    outs = await fill_correct(env, cells)
    assert [o.finished for o in outs] == [False] * (len(cells) - 1) + [True]
    assert all(o.reward > 0 for o in outs)
    assert sum(o.reward for o in outs) == 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ONE_PER_VARIANT, ids=lambda t: t["id"])
async def test_two_invalid_moves_at_start_score_zero(task):
    env = await new_env(task)
    r, c, _, wrong = empty_cells(env)[0]
    first = await place(env, r, c, wrong)
    assert not first.finished
    second = await place(env, r, c, wrong)
    assert second.finished
    assert first.reward + second.reward == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ONE_PER_VARIANT[2:], ids=lambda t: t["id"])
async def test_invalid_ending_pays_no_more_than_progress(task):
    env = await new_env(task)
    cells = empty_cells(env)
    k = int(0.8 * len(cells))
    outs = await fill_correct(env, cells[:k])
    r, c, _, wrong = cells[k]
    outs.append(await place(env, r, c, wrong))
    outs.append(await place(env, r, c, wrong))
    assert outs[-1].finished and not any(o.finished for o in outs[:-1])
    assert outs[-1].reward == 0.0 and outs[-2].reward == 0.0
    total = sum(o.reward for o in outs)
    assert total == pytest.approx(k / len(cells), abs=1e-12)
    rewards, _ = env.ta_env.close()
    assert total == pytest.approx(rewards[0], abs=1e-12)


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ONE_PER_VARIANT[2:], ids=lambda t: t["id"])
async def test_partial_progress_is_banked_without_a_terminal(task):
    env = await new_env(task)
    cells = empty_cells(env)
    k = int(0.8 * len(cells))
    outs = await fill_correct(env, cells[:k])
    assert not any(o.finished for o in outs)
    assert sum(o.reward for o in outs) == pytest.approx(k / len(cells), abs=1e-12)


@pytest.mark.asyncio
async def test_invalid_warning_resets_after_a_valid_move():
    env = await new_env(TASKS[100])
    cells = empty_cells(env)
    (r0, c0, _, w0), (r1, c1, s1, _), (r2, c2, _, w2) = cells[:3]
    a = await place(env, r0, c0, w0)
    b = await place(env, r1, c1, s1)
    c = await place(env, r2, c2, w2)
    assert not (a.finished or b.finished or c.finished)
    assert a.reward == 0.0 and c.reward == 0.0
    assert b.reward == pytest.approx(1 / len(cells))


@pytest.mark.asyncio
async def test_progress_cannot_be_paid_twice():
    task = TASKS[100]
    env = await new_env(task)
    cells = empty_cells(env)
    paid = sum(o.reward for o in await fill_correct(env, cells[:5]))
    r, c, sol, _ = cells[0]
    again = await place(env, r, c, sol)
    assert again.reward == 0.0 and not again.finished
    # A fresh board under the same session must not pay the same cells again.
    await env.get_prompt()
    refill = await fill_correct(env, cells[:5])
    assert sum(o.reward for o in refill) == 0.0
    nxt = await place(env, *cells[5][:3])
    assert nxt.reward == pytest.approx(1 / len(cells))
    assert paid + nxt.reward == pytest.approx(6 / len(cells))


@pytest.mark.asyncio
async def test_moves_after_game_over_pay_nothing():
    env = await new_env(TASKS[0])
    await fill_correct(env, empty_cells(env))
    out = await place(env, 1, 1, 1)
    assert out.finished and out.reward == 0.0

