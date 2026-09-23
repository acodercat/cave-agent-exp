from typing import List, Dict, Any, Union, Tuple, Set 
def vegan_restaurant_find_nearby(location:str, operating_hours:int=None) -> str:
	"""
	vegan_restaurant_find_nearby : Locate nearby vegan restaurants based on specific criteria like operating hours.    
	Parameters:
	location (str): The city and state, e.g. New York, NY, you should format it as City, State.
	operating_hours (int): Preferred latest closing time of the restaurant. E.g. if 11 is given, then restaurants that close at or after 11 PM will be considered. This is in 24 hour format. Default is 24.

	Required Parameter = [location,]

	"""
	return 'Success'

tools = [vegan_restaurant_find_nearby]
