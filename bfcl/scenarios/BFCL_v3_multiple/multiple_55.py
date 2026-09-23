from typing import List, Dict, Any, Union, Tuple, Set 
def stock_forecast(company:str, days:int, model:str=None) -> str:
	"""
	stock_forecast : Predict the future stock price for a specific company and time frame.    
	Parameters:
	company (str): The company that you want to get the stock price prediction for.
	days (int): Number of future days for which to predict the stock price.
	model (str): The model to use for prediction. Default 'regression'

	Required Parameter = [company,days,]

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

tools = [stock_forecast, weather_forecast]
