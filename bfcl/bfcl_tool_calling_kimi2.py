import asyncio
import json
# from adapters.llama_index_agent_adapter import LLamaIndexAgentFactory
# from llama_index.llms.openai_like import OpenAILike
from adapters.litellm_adapter import LitellmAgentFactory
from adapters.litellm_adapter import LitellmModel
from evaluation import evaluate
import os
from datetime import datetime

file_names = []

file_names.append("./scenarios/BFCL_v3_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_parallel_multiple_ground_truth.json")
file_names.append("./scenarios/BFCL_v3_simple_ground_truth.json")
run_id = "run_3"
async def process_and_evaluate_llamaindex(file_name: str):
     with open(file_name, 'r', encoding='utf-8') as f:
        ground_truths = json.load(f)

        model_id = "kimi-k2-0905-preview"
        api_key = os.environ["MOONSHOT_API_KEY"]
        base_url = "https://api.moonshot.cn/v1"
    

        model = LitellmModel(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=0.6,
            provider="openai"
        )
        agent_factory = LitellmAgentFactory(model)
        os.makedirs("./results/tool_calling/"+ model_id+"_"+run_id, exist_ok=True)

        output_file = file_name.replace("./scenarios/","./results/tool_calling/"+ model_id+"_"+run_id+"/")
        output_file = output_file.replace("_ground_truth","")
        
        await evaluate(agent_factory, ground_truths, output_file)
    
       

async def main():

    # max_concurrent_tasks = 1
    # semaphore = asyncio.Semaphore(max_concurrent_tasks)
    # tasks = [process_and_evaluate_llamaindex(file_name, semaphore) for file_name in file_names]
    for file_name in file_names:
        await process_and_evaluate_llamaindex(file_name)
    
    print("all tasks is done")

if __name__ == "__main__":
    asyncio.run(main())