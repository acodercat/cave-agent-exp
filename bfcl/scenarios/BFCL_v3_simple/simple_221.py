from typing import List, Dict, Any, Union, Tuple, Set 
def population_growth_estimate(location:str, years:int, rate:float=None) -> str:
	"""
	population_growth_estimate : Estimate the future population growth of a specific location over a specified time period.    
	Parameters:
	location (str): The city that you want to estimate the population growth for.
	years (int): Number of years into the future for the estimate.
	rate (float): Expected annual growth rate in percentage. Default is 1.2.

	Required Parameter = [location,years,]

	"""
	return 'Success'

tools = [population_growth_estimate]
