from typing import List, Dict, Any, Union, Tuple, Set 
def database_us_census_get_population(area:str, type:str, year:int=2000) -> str:
	"""
	database_us_census_get_population : Fetch population data from US Census database.    
	Parameters:
	area (str): Name of the city, state, or country.
	type (str): Specify whether the area is city/state/country.
	year (int): Year of the data

	Required Parameter = [area,type,]

	"""
	return 'Success'

tools = [database_us_census_get_population]
