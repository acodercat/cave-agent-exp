from typing import List, Dict, Any, Union, Tuple, Set 
def map_service_get_directions(start:str, end:str, avoid:List[str]=None) -> str:
	"""
	map_service_get_directions : Retrieve directions from a starting location to an ending location, including options for route preferences.    
	Parameters:
	start (str): Starting location for the route.
	end (str): Ending location for the route.
	avoid (List[str]): Route features to avoid. Default is ['highways', 'ferries']

	Required Parameter = [start,end,]

	"""
	return 'Success'

tools = [map_service_get_directions]
