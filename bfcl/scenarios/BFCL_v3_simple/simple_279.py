from typing import List, Dict, Any, Union, Tuple, Set 
def instrument_price_get(brand:str, model:str, finish:str) -> str:
	"""
	instrument_price_get : Retrieve the current retail price of a specific musical instrument.    
	Parameters:
	brand (str): The brand of the instrument.
	model (str): The specific model of the instrument.
	finish (str): The color or type of finish on the instrument.

	Required Parameter = [brand,model,finish,]

	"""
	return 'Success'

tools = [instrument_price_get]
