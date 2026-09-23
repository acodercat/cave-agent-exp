from typing import List, Dict, Any, Union, Tuple, Set 
def maps_shortest_path(start_location:str, end_location:str, mode:str='walk') -> str:
	"""
	maps_shortest_path : Find the shortest path from one location to another by using a specific mode of transportation.    
	Parameters:
	start_location (str): The name or coordinates of the start location.
	end_location (str): The name or coordinates of the end location.
	mode (str): The mode of transportation (walk, bike, transit, drive).

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def maps_route_times(route:str, mode:str='walk') -> str:
	"""
	maps_route_times : Estimates the time it will take to travel from one location to another by a specific mode of transportation.    
	Parameters:
	route (str): The string representation of the route.  Format is location 1 to location 2
	mode (str): The mode of transportation (walk, bike, transit, drive).

	Required Parameter = [route,]

	"""
	return 'Success'

tools = [maps_shortest_path, maps_route_times]
