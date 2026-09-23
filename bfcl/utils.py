import tomllib
from typing import TypedDict, Callable
from agents import Agent as OpenAIAgent, function_tool

class ModelConfig(TypedDict):
    model_id: str
    api_key: str
    base_url: str

def load_model_config(model_name: str) -> ModelConfig:
    """Load model configuration from models.toml"""
    with open("models.toml", "rb") as f:
        models = tomllib.load(f)
    
    if model_name not in models:
        available = list(models.keys())
        raise ValueError(f"Model '{model_name}' not found. Available: {available}")
    
    return models[model_name]


def fix_array_schema(schema: dict) -> dict:
    """
    Recursively fix array schemas to include 'items' property if missing.
    OpenAI requires all array types to have an 'items' definition.
    """
    if not isinstance(schema, dict):
        return schema

    result = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = fix_array_schema(value)
        elif isinstance(value, list):
            result[key] = [fix_array_schema(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value

    # If this is an array type without items, add a default items schema
    if result.get("type") == "array" and "items" not in result:
        result["items"] = {"type": "number"}

    return result


def function_to_schema(func: Callable) -> dict:
    """
    Convert a Python function to an OpenAI tool schema.
    """

    tool = function_tool(func, strict_mode=False)
    params_schema = fix_array_schema(tool.params_json_schema)
    return {
            "name": func.__name__,
            "description": func.__doc__ or tool.description,
            "parameters": params_schema
        }

# if __name__ == "__main__":
#     from typing import List, Dict, Any, Union, Tuple, Set 
#     def find_flute(brand:str, specs:List[str]):
#         """
#         find_flute : Locate a flute for sale based on specific requirements.    
#         Parameters:
#         brand (str): The brand of the flute. Example, 'Yamaha'
#         specs (List[str]): The specifications of the flute desired.

#         Required Parameter = [brand,specs,]

#         """
#         return 'Success'

#     from typing import List, Dict, Any, Union, Tuple, Set 
#     def calculate_genotype_frequency(allele_frequency:float, genotype:str):
#         """
#         calculate_genotype_frequency : Calculate the frequency of homozygous dominant genotype based on the allele frequency using Hardy Weinberg Principle.    
#         Parameters:
#         allele_frequency (float): The frequency of the dominant allele in the population.
#         genotype (str): The genotype which frequency is needed, default is homozygous dominant. 

#         Required Parameter = [allele_frequency,genotype,]

#         """
#         return 'Success'

#     from typing import List, Dict, Any, Union, Tuple, Set 
#     def math_factorial(number:int):
#         """
#         math_factorial : Calculate the factorial of a given number.    
#         Parameters:
#         number (int): The number for which factorial needs to be calculated.

#         Required Parameter = [number,]

#         """
#         return 'Success'
#     function_to_schema(math_factorial)
#     tools = [find_flute, calculate_genotype_frequency, math_factorial]
