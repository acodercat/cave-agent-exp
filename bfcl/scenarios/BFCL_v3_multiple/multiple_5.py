from typing import List, Dict, Any, Union, Tuple, Set 
def weather_get_by_city_date(city:str, date:str) -> str:
	"""
	weather_get_by_city_date : Retrieves the historical weather data based on city and date.    
	Parameters:
	city (str): The city for which to retrieve the weather.
	date (str): The date for which to retrieve the historical weather data in the format YYYY-MM-DD.

	Required Parameter = [city,date,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_get_forecast_by_coordinates(coordinates:Tuple[float], days_ahead:int=None) -> str:
	"""
	weather_get_forecast_by_coordinates : Get the weather forecast for a specific geographical coordinates.    
	Parameters:
	coordinates (Tuple[float]): The geographical coordinates for which to retrieve the weather. The first element of the tuple is the latitude and the second is the longitude.
	days_ahead (int): Number of days to forecast from current date (optional, default is 7).

	Required Parameter = [coordinates,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_get_by_coordinates_date(coordinates:Tuple[float], date:str) -> str:
	"""
	weather_get_by_coordinates_date : Retrieves the historical weather data based on coordinates and date.    
	Parameters:
	coordinates (Tuple[float]): The geographical coordinates for which to retrieve the weather. The first element of the tuple is the latitude and the second is the longitude.
	date (str): The date for which to retrieve the historical weather data in the format YYYY-MM-DD.

	Required Parameter = [coordinates,date,]

	"""
	return 'Success'

tools = [weather_get_by_city_date, weather_get_forecast_by_coordinates, weather_get_by_coordinates_date]
