from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast_detailed(location:str, days:int, details:bool=False) -> str:
	"""
	weather_forecast_detailed : Retrieve a detailed weather forecast for a specific city like Boston and time frame.    
	Parameters:
	location (str): The city that you want to get the weather for.
	days (int): Number of days for the forecast.
	details (bool): Provide detailed weather information or not.

	Required Parameter = [location,days,]

	"""
	return 'Success'

tools = [weather_forecast_detailed]
