from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast_precipitation(location:str, days:int) -> str:
	"""
	weather_forecast_precipitation : Retrieve a precipitation forecast for a specific location for a certain number of days.    
	Parameters:
	location (str): The city that you want to get the precipitation forecast for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast_humidity(location:str, days:int) -> str:
	"""
	weather_forecast_humidity : Retrieve a humidity forecast for a specific location for a certain number of days.    
	Parameters:
	location (str): The city that you want to get the humidity forecast for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast_temperature(location:str, days:int) -> str:
	"""
	weather_forecast_temperature : Retrieve a temperature forecast for a specific location for a certain number of days.    
	Parameters:
	location (str): The city that you want to get the temperature forecast for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

	"""
	return 'Success'

tools = [weather_forecast_precipitation, weather_forecast_humidity, weather_forecast_temperature]
