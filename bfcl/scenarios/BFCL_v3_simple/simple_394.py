from typing import List, Dict, Any, Union, Tuple, Set 
def maps_get_distance_duration(start_location:str, end_location:str, traffic:bool=None) -> str:
	"""
	maps_get_distance_duration : Retrieve the travel distance and estimated travel time from one location to another via car    
	Parameters:
	start_location (str): Starting point of the journey
	end_location (str): Ending point of the journey
	traffic (bool): If true, considers current traffic. Default is false.

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

tools = [maps_get_distance_duration]
