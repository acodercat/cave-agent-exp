from typing import List, Dict, Any, Union, Tuple, Set 
def current_weather_condition(city:str, country:str, measurement:str=None) -> str:
	"""
	current_weather_condition : Get the current weather conditions of a specific city including temperature and humidity.    
	Parameters:
	city (str): The city that you want to get the current weather conditions for.
	country (str): The country of the city you specified.
	measurement (str): You can specify which unit to display the temperature in, 'c' for Celsius, 'f' for Fahrenheit. Default is 'c'.

	Required Parameter = [city,country,]

	"""
	return 'Success'

tools = [current_weather_condition]
