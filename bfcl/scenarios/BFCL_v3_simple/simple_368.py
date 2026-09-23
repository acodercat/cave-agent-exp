from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_cooking_time(weight_kg:float, cooking_method:str=None, temp_celsius:int=None) -> str:
	"""
	calculate_cooking_time : Calculate the cooking time for a roast chicken.    
	Parameters:
	weight_kg (float): The weight of the chicken in kilograms.
	cooking_method (str): The method of cooking, defaults to 'roast'.
	temp_celsius (int): The cooking temperature in degrees celsius, defaults to 180.

	Required Parameter = [weight_kg,]

	"""
	return 'Success'

tools = [calculate_cooking_time]
