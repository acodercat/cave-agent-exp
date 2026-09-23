from typing import List, Dict, Any, Union, Tuple, Set 
def get_current_time(city:str, country:str, format:str=None) -> str:
	"""
	get_current_time : Retrieve the current time for a specified city and country.    
	Parameters:
	city (str): The city for which the current time is to be retrieved.
	country (str): The country where the city is located.
	format (str): The format in which the time is to be displayed, optional (defaults to 'HH:MM:SS').

	Required Parameter = [city,country,]

	"""
	return 'Success'

tools = [get_current_time]
