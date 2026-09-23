from typing import List, Dict, Any, Union, Tuple, Set 
def get_crime_rate(city:str, state:str, type:str=None, year:int=None) -> str:
	"""
	get_crime_rate : Retrieve the official crime rate of a city.    
	Parameters:
	city (str): The name of the city.
	state (str): The state where the city is located.
	type (str): Optional. The type of crime. Default is 'violent'
	year (int): Optional. The year for the crime rate data. Default is year 2001.

	Required Parameter = [city,state,]

	"""
	return 'Success'

tools = [get_crime_rate]
