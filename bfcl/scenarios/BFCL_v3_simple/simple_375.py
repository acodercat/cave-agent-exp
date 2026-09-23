from typing import List, Dict, Any, Union, Tuple, Set 
def walmart_check_price(items:List[str], quantities:List[int], store_location:str=None) -> str:
	"""
	walmart_check_price : Calculate total price for given items and their quantities at Walmart.    
	Parameters:
	items (List[str]): List of items to be priced.
	quantities (List[int]): Quantity of each item corresponding to the items list.
	store_location (str): The store location for specific pricing (optional). Default to all if not specified.

	Required Parameter = [items,quantities,]

	"""
	return 'Success'

tools = [walmart_check_price]
