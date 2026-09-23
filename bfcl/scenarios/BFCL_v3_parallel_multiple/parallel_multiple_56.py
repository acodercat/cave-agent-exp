from typing import List, Dict, Any, Union, Tuple, Set 
def time_zones_get_current_time(location:str) -> str:
	"""
	time_zones_get_current_time : Retrieve current time for the specified location    
	Parameters:
	location (str): The city that you want to get the current time for.

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def time_zones_get_time_difference(city_1:str, city_2:str) -> str:
	"""
	time_zones_get_time_difference : Retrieve the time difference between two cities    
	Parameters:
	city_1 (str): First city for calculating the time difference.
	city_2 (str): Second city for calculating the time difference.

	Required Parameter = [city_1,city_2,]

	"""
	return 'Success'

tools = [time_zones_get_current_time, time_zones_get_time_difference]
