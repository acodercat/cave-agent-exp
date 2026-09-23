from typing import List, Dict, Any, Union, Tuple, Set 
def safeway_order(location:str, items:List[str], quantity:List[int]) -> str:
	"""
	safeway_order : Order specified items from a Safeway location.    
	Parameters:
	location (str): The location of the Safeway store, e.g. Palo Alto, CA.
	items (List[str]): List of items to order.
	quantity (List[int]): Quantity of each item in the order list.

	Required Parameter = [location,items,quantity,]

	"""
	return 'Success'

tools = [safeway_order]
