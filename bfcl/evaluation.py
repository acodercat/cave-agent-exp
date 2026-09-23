import json
import logging
import os
import importlib
import numpy as np
import pandas as pd
from tqdm import tqdm
from core.evaluator import AgentEvaluator


class ExtendedEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy and pandas types."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        if isinstance(obj, pd.Series):
            return obj.tolist()
        return super().default(obj)



async def evaluate(agent_factory, ground_truths, results_file):

    logger = logging.getLogger(results_file)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    handler = logging.FileHandler(results_file, mode='a', encoding='utf-8', delay=False)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    completed_scenarios = set()
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        result_obj = json.loads(line)
                        if not isinstance(result_obj, dict):
                            break
                        if 'scenario' in result_obj:
                            completed_scenarios.add(result_obj['scenario'])
                    except TypeError:
                        print("wrong type result_obj")
                    except json.JSONDecodeError:
                        print(f"Warning: Found a line in the results file that cannot be parsed: {line.strip()}")
                    except Exception as e:
                        print(f"failed，error: {e}")


    except FileNotFoundError:
        print("Results file not found, a new file will be created.")

    evaluator = AgentEvaluator(agent_factory)
   
    for ground_truth in tqdm(ground_truths, desc="Evaluating scenarios"):
        if not ground_truth:
            logger.info("Warning: Found an empty ground truth entry, skipping.")
            continue
        try:
            scenario_name = ground_truth['scenario']
            
            if scenario_name in completed_scenarios:
                # print(f"Skipping already evaluated scenario: {scenario_name}") # 可以取消注释来显示跳过信息
                continue

            if not ground_truth["conversations"]:
                logger.info(json.dumps({"scenario": scenario_name, "error": "conversations is not exist"}))
                continue

            scenario_module = importlib.import_module(ground_truth['module'])
            results = await evaluator.evaluate(scenario_name, scenario_module, ground_truth['conversations'])
            
            results['scenario_name'] = scenario_name
            
            try:
                # json_string = json.dumps(results, indent=2, ensure_ascii=False)
                json_string = json.dumps(results, ensure_ascii=False, cls=ExtendedEncoder)
                logger.info(json_string)
                handler.flush()
                
                completed_scenarios.add(scenario_name)
                
                # print(f"completed: {scenario_name}, metric: {results.get('metrics', 'N/A')}")

            except Exception as e:
                print(json.dumps({"scenario": scenario_name, "error": f"processing '{scenario_name}' failed，error: {e}"}))
                handler.flush()
                
        except Exception as e:
            scenario_name_for_error = ground_truth.get('scenario', 'unknown scenario')
            
            print(json.dumps({"scenario": scenario_name_for_error, "Serious error": f"evaluate '{scenario_name_for_error}'  Serious error: {e}"}))
            handler.flush()
            continue