from typing import List, Dict, Any, Union, Tuple, Set 
def detailed_weather_forecast(location:str, duration:int, include_precipitation:bool=None) -> str:
	"""
	detailed_weather_forecast : Retrieve a detailed weather forecast for a specific location and duration including optional precipitation details.    
	Parameters:
	location (str): The city name that you want to get the weather for.
	duration (int): Duration in hours for the detailed forecast.
	include_precipitation (bool): Whether to include precipitation data in the forecast. Default is false.

	Required Parameter = [location,duration,]

	"""
	return 'Success'

tools = [detailed_weather_forecast]
