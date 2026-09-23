from typing import List, Dict, Any, Union, Tuple, Set 
def get_traffic_info(start_location:str, end_location:str, mode:str=None) -> str:
	"""
	get_traffic_info : Retrieve current traffic conditions for a specified route.    
	Parameters:
	start_location (str): The starting point of the route.
	end_location (str): The destination of the route.
	mode (str): Preferred method of transportation, default to 'driving'.

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

tools = [get_traffic_info]
