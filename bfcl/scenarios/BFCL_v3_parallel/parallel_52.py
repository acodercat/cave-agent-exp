from typing import List, Dict, Any, Union, Tuple, Set 
def restaurant_finder(location:str, cuisine:str, preferences:List[str]=None) -> str:
	"""
	restaurant_finder : Search for restaurants based on location, cuisine type and other preferences.    
	Parameters:
	location (str): City and state, e.g. New York, NY.
	cuisine (str): Type of cuisine the user is interested in, e.g. Italian, Japanese etc.
	preferences (List[str]): Extra features in the restaurant. default is ['Delivery'].

	Required Parameter = [location,cuisine,]

	"""
	return 'Success'

tools = [restaurant_finder]
