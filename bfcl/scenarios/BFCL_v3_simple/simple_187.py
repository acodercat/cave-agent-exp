from typing import List, Dict, Any, Union, Tuple, Set 
def get_current_weather(location:str, include_temperature:bool=None, include_humidity:bool=None) -> str:
	"""
	get_current_weather : Retrieves the current temperature and humidity for a specific location.    
	Parameters:
	location (str): The city name to get the weather for.
	include_temperature (bool): Whether to include the temperature in the result. Default is true.
	include_humidity (bool): Whether to include the humidity in the result. Default is true.

	Required Parameter = [location,]

	"""
	return 'Success'

tools = [get_current_weather]
