from typing import List, Dict, Any, Union, Tuple, Set 
def forest_growth_forecast(location:str, years:int, include_human_impact:bool=None) -> str:
	"""
	forest_growth_forecast : Predicts the forest growth over the next N years based on current trends.    
	Parameters:
	location (str): The location where you want to predict forest growth.
	years (int): The number of years for the forecast.
	include_human_impact (bool): Whether or not to include the impact of human activities in the forecast. If not provided, defaults to false.

	Required Parameter = [location,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_scientist_for_discovery(discovery:str) -> str:
	"""
	get_scientist_for_discovery : Retrieve the scientist's name who is credited for a specific scientific discovery or theory.    
	Parameters:
	discovery (str): The scientific discovery or theory.

	Required Parameter = [discovery,]

	"""
	return 'Success'

tools = [forest_growth_forecast, get_scientist_for_discovery]
