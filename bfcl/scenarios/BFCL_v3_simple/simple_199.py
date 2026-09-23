from typing import List, Dict, Any, Union, Tuple, Set 
def environmental_data_air_quality_index(location:str, days:int=None) -> str:
	"""
	environmental_data_air_quality_index : Retrieves Air Quality Index (AQI) for specified location over a number of days.    
	Parameters:
	location (str): Name of the city or town to retrieve air quality index for.
	days (int): Number of days for which to retrieve data. If not provided, default to today.

	Required Parameter = [location,]

	"""
	return 'Success'

tools = [environmental_data_air_quality_index]
