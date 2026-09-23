from typing import List, Dict, Any, Union, Tuple, Set 
def grocery_delivery_order(location:str, items:List[str], max_delivery_cost:float=None) -> str:
	"""
	grocery_delivery_order : Order grocery items from a specific location with optional delivery price limit    
	Parameters:
	location (str): The location of the grocery store
	items (List[str]): List of items to order
	max_delivery_cost (float): The maximum delivery cost. It is optional. Default 1000000

	Required Parameter = [location,items,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def ride_hailing_get_rides(source:str, destination:str, max_cost:int=None) -> str:
	"""
	ride_hailing_get_rides : Find ride from source to destination with an optional cost limit    
	Parameters:
	source (str): The starting point of the journey
	destination (str): The endpoint of the journey
	max_cost (int): The maximum cost of the ride. It is optional. Default is 1000000

	Required Parameter = [source,destination,]

	"""
	return 'Success'

tools = [grocery_delivery_order, ride_hailing_get_rides]
