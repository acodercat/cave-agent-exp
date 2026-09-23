from typing import List, Dict, Any, Union, Tuple, Set 
def paint_color_trends(room:str, period:str=None) -> str:
	"""
	paint_color_trends : Find the most popular paint color for a specific area in the home.    
	Parameters:
	room (str): Type of the room e.g. Living room, Bathroom etc.
	period (str): The period over which to check the paint color trend. Default is 'Monthly' if not specified.

	Required Parameter = [room,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def weather_forecast(location:str, days:int) -> str:
	"""
	weather_forecast : Retrieve a weather forecast for a specific location and time frame.    
	Parameters:
	location (str): The city that you want to get the weather for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def house_price_trends(location:str, period:str=None) -> str:
	"""
	house_price_trends : Find the average house price in a specific area.    
	Parameters:
	location (str): City and state, e.g. New York, NY.
	period (str): The period over which to check the price trend. Default is 'Yearly' if not specified.

	Required Parameter = [location,]

	"""
	return 'Success'

tools = [paint_color_trends, weather_forecast, house_price_trends]
