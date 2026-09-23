from typing import List, Dict, Any, Union, Tuple, Set 
def get_air_quality_index(location:str, time:str) -> str:
	"""
	get_air_quality_index : Retrieve the air quality index at a specified location and time.    
	Parameters:
	location (str): The location to get the air quality index for.
	time (str): The specific time to check the air quality. Default is the current time.

	Required Parameter = [location,time,]

	"""
	return 'Success'

tools = [get_air_quality_index]
