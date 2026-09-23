from typing import List, Dict, Any, Union, Tuple, Set 
def restaurant_find(cuisine:str, price:List[str]=None) -> str:
	"""
	restaurant_find : Locate restaurants based on specific criteria such as cuisine and price range    
	Parameters:
	cuisine (str): The type of cuisine preferred.
	price (List[str]): Price range of the restaurant in format ['low', 'mid', 'high']. Default is 'mid' if not specified.

	Required Parameter = [cuisine,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def recipe_find(mainIngredient:str, ingredientLimit:int) -> str:
	"""
	recipe_find : Locate cooking recipes based on specific criteria such as main ingredient and number of ingredients    
	Parameters:
	mainIngredient (str): Main ingredient for the recipe.
	ingredientLimit (int): Max number of ingredients the recipe should use.

	Required Parameter = [mainIngredient,ingredientLimit,]

	"""
	return 'Success'

tools = [restaurant_find, recipe_find]
