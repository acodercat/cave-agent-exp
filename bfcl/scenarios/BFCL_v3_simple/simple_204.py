from typing import List, Dict, Any, Union, Tuple, Set 
def restaurant_find_nearby(location:str, cuisine:str, max_distance:int=None) -> str:
	"""
	restaurant_find_nearby : Locate nearby restaurants based on specific criteria like cuisine type.    
	Parameters:
	location (str): The city and state, e.g. Seattle, WA
	cuisine (str): Preferred type of cuisine in restaurant.
	max_distance (int): Maximum distance (in miles) within which to search for restaurants. Default is 5.

	Required Parameter = [location,cuisine,]

	"""
	return 'Success'

tools = [restaurant_find_nearby]
