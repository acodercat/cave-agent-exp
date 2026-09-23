from typing import List, Dict, Any, Union, Tuple, Set 
def air_quality_forecast(location:str, days:int) -> str:
	"""
	air_quality_forecast : Retrieve an air quality forecast for a specific location and time frame.    
	Parameters:
	location (str): The city that you want to get the air quality forecast for.
	days (int): Number of days for the forecast.

	Required Parameter = [location,days,]

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
def news(topic:str, days:int) -> str:
	"""
	news : Retrieve news articles for a specific topic.    
	Parameters:
	topic (str): The topic that you want to get the news for.
	days (int): Number of past days for which to retrieve the news.

	Required Parameter = [topic,days,]

	"""
	return 'Success'

tools = [air_quality_forecast, weather_forecast, news]
