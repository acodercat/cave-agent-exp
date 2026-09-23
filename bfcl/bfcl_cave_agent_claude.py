import asyncio
from adapters.cave_agent_adapter import CaveAgentFactory
from cave_agent.models import OpenAIServerModel, LiteLLMModel
from evaluation import evaluate
import json
import os
file_names = []

file_names.append("./scenarios/BFCL_v3_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_simple_ground_truth.json")
run_id = "run_1"
async def process_and_evaluate(file_name: str, semaphore: asyncio.Semaphore):
    async with semaphore:

        with open(file_name, 'r', encoding='utf-8') as f:
            ground_truths = json.load(f)

        model_id = "claude-sonnet-4-5-20250929"
        api_key = os.environ["ANTHROPIC_API_KEY"]
    

        model = LiteLLMModel(
            model_id=model_id,
            api_key=api_key,
            temperature=0.2,
            # provider="anthropic"
        )
        agent_factory = CaveAgentFactory(model)


        os.makedirs("./results/cave_agent/"+ model_id+"_"+run_id, exist_ok=True)

        output_file = file_name.replace("./scenarios/","./results/cave_agent/"+ model_id+"_"+run_id+"/")
        output_file = output_file.replace("_ground_truth","")

        await evaluate(agent_factory, ground_truths, output_file)

async def main():

    max_concurrent_tasks = 1
    semaphore = asyncio.Semaphore(max_concurrent_tasks)

    tasks = [process_and_evaluate(file_name, semaphore) for file_name in file_names]
    
    await asyncio.gather(*tasks)
    
    print("all tasks are done")

if __name__ == "__main__":
    asyncio.run(main())