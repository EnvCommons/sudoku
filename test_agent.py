import asyncio
import json
import os
from openai import AsyncOpenAI
from env import SudokuEnvironment, PlaceNumberParams


def get_secrets():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    secrets = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    secrets[key.strip().lower()] = val.strip()
    return secrets


async def run_agent_test(max_turns=100):
    secrets = get_secrets()
    oai_client = AsyncOpenAI(api_key=secrets.get("openai_api_key"))

    tasks = SudokuEnvironment.list_tasks(split="test")
    task = tasks[0]

    print(f"=== Agent Test: Sudoku ===")
    print(f"Task: {task['id']}")

    env = SudokuEnvironment(task_spec=task, secrets=secrets)
    prompt = await env.get_prompt()

    tools = [
        {
            "type": "function",
            "name": "place_number",
            "description": "Place a number (1-9) at the given row (1-9) and column (1-9) on the Sudoku board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row": {"type": "integer", "description": "Row (1-9)"},
                    "column": {"type": "integer", "description": "Column (1-9)"},
                    "number": {"type": "integer", "description": "Number to place (1-9)"},
                },
                "required": ["row", "column", "number"],
                "additionalProperties": False,
            },
        }
    ]

    input_list = [{"role": "user", "content": prompt[0].text}]
    finished = False
    turn = 0

    while not finished and turn < max_turns:
        turn += 1
        response = await oai_client.responses.create(
            model="gpt-5.2",
            tools=tools,
            input=input_list,
        )

        input_list += response.output

        for item in response.output:
            if item.type == "function_call":
                args = json.loads(str(item.arguments))
                result = await env.place_number(PlaceNumberParams(**args))

                finished = result.finished
                reward = result.reward

                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result.blocks[0].text,
                })

                if turn % 10 == 0 or finished:
                    print(f"  Turn {turn}: ({args.get('row')},{args.get('column')})={args.get('number')}, reward={reward:.3f}, finished={finished}")

                if finished:
                    print(f"\n=== FINISHED! Final reward: {reward:.3f} ===")
                    break

    if not finished:
        print(f"\n=== Hit max turns ({max_turns}) without finishing ===")


if __name__ == "__main__":
    asyncio.run(run_agent_test())
