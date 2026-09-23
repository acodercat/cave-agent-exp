from typing import List, Dict, Any, Union, Tuple, Set 
def recipe_finder_find(servings:int, diet:str, prep_time:int=None) -> str:
	"""
	recipe_finder_find : Find a recipe based on dietary preferences, number of servings, and preparation time.    
	Parameters:
	servings (int): The number of people that the recipe should serve.
	diet (str): Any dietary restrictions like 'vegan', 'vegetarian', 'gluten-free' etc.
	prep_time (int): The maximum amount of time (in minutes) the preparation should take. Default is 60 minutes.

	Required Parameter = [servings,diet,]

	"""
	return 'Success'

tools = [recipe_finder_find]
