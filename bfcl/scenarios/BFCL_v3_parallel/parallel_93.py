from typing import List, Dict, Any, Union, Tuple, Set 
def route_estimate_time(start_location:str, end_location:str, stops:List[str]=['NYC']) -> str:
	"""
	route_estimate_time : Estimate the travel time for a specific route with optional stops.    
	Parameters:
	start_location (str): The starting point for the journey.
	end_location (str): The destination for the journey.
	stops (List[str]): Additional cities or points of interest to stop at during the journey ordered.

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

tools = [route_estimate_time]
