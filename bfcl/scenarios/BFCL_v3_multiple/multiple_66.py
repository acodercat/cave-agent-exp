from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_distance(start_point:str, end_point:str) -> str:
	"""
	calculate_distance : Calculate distance between two locations.    
	Parameters:
	start_point (str): Starting point of the journey.
	end_point (str): Ending point of the journey.

	Required Parameter = [start_point,end_point,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def traffic_estimate(start_location:str, end_location:str, time_period:str=None) -> str:
	"""
	traffic_estimate : Estimate traffic from one location to another for a specific time period.    
	Parameters:
	start_location (str): Starting location for the journey.
	end_location (str): Ending location for the journey.
	time_period (str): Specify a time frame to estimate the traffic, 'now' for current, 'weekend' for the coming weekend. Default 'now'

	Required Parameter = [start_location,end_location,]

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

tools = [calculate_distance, traffic_estimate, weather_forecast]
