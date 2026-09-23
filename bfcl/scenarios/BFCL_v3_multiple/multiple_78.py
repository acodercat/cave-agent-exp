from typing import List, Dict, Any, Union, Tuple, Set 
def tourist_spot_info(spot:str, city:str, details:List[str]='timing, attractions') -> str:
	"""
	tourist_spot_info : Retrieve information about a specific tourist spot.    
	Parameters:
	spot (str): The name of the tourist spot you want to get information for.
	city (str): The city where the tourist spot is located.
	details (List[str]): Details of the tourist spot to get information on. For multiple details, separate them by comma.

	Required Parameter = [spot,city,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def museum_info(museum:str, city:str, features:List[str]='timings, exhibitions') -> str:
	"""
	museum_info : Retrieve information about a specific museum.    
	Parameters:
	museum (str): The name of the museum you want to get information for.
	city (str): The city where the museum is located.
	features (List[str]): Features of the museum to get information on. For multiple features, separate them by comma.

	Required Parameter = [museum,city,]

	"""
	return 'Success'

tools = [tourist_spot_info, museum_info]
