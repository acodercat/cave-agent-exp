from typing import List, Dict, Any, Union, Tuple, Set 
def detailed_weather_forecast(location:str, days:int, details:List[str]) -> str:
	"""
	detailed_weather_forecast : Retrieve a detailed weather forecast for a specific location and time frame, including high/low temperatures, humidity, and precipitation.    
	Parameters:
	location (str): The city that you want to get the weather for.
	days (int): Number of days for the forecast.
	details (List[str]): Specific weather details required in the forecast.

	Required Parameter = [location,days,details,]

	"""
	return 'Success'

tools = [detailed_weather_forecast]
