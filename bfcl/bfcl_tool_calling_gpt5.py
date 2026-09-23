import asyncio
import json
from adapters.litellm_adapter import LitellmAgentFactory
from adapters.litellm_adapter import LitellmModel
from evaluation import evaluate
import os

file_names = []

file_names.append("./scenarios/BFCL_v3_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_simple_ground_truth.json")
run_id = "run_2"
async def process_and_evaluate_llamaindex(file_name: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        with open(file_name, 'r', encoding='utf-8') as f:
            ground_truths = json.load(f)

            model_id = "gpt-5.1"
            api_key = os.environ["OPENAI_API_KEY"]
            base_url = "https://api.openai.com/v1"
        

            model = LitellmModel(
                model_id=model_id,
                api_key=api_key,
                base_url=base_url,
                provider="openai"
            )
            agent_factory = LitellmAgentFactory(model)
            os.makedirs("./results/tool_calling/"+ model_id+"_"+run_id, exist_ok=True)

            output_file = file_name.replace("./scenarios/","./results/tool_calling/"+ model_id+"_"+run_id+"/")
            output_file = output_file.replace("_ground_truth","")
            
            await evaluate(agent_factory, ground_truths, output_file)
    
       

async def main():

    max_concurrent_tasks = 4
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    tasks = [process_and_evaluate_llamaindex(file_name, semaphore) for file_name in file_names]
    # for file_name in file_names:
    #     await process_and_evaluate_llamaindex(file_name)
    
    await asyncio.gather(*tasks)
    
    print("all tasks are done")

if __name__ == "__main__":
    asyncio.run(main())