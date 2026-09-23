from typing import List, Dict, Any, Union, Tuple, Set 
def recipe_search(diet:List[str], dish:str, time_limit:int=None) -> str:
	"""
	recipe_search : Search for a cooking recipe based on specific dietary needs and time constraint.    
	Parameters:
	diet (List[str]): Specific dietary need.
	time_limit (int): The maximum time to prepare the recipe in minutes. Default is 60 minutes.
	dish (str): The name of the dish to search for. Default is not use if not specified.

	Required Parameter = [dish,diet,]

	"""
	return 'Success'

tools = [recipe_search]
