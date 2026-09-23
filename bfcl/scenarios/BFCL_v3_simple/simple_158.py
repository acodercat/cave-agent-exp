from typing import List, Dict, Any, Union, Tuple, Set 
def get_criminal_records(name:str, location:str, from_year:int, to_year:int) -> str:
	"""
	get_criminal_records : Retrieve the criminal records of a specific person in a specific area during a certain time period.    
	Parameters:
	name (str): The name of the person.
	location (str): The city and state, e.g. New York, NY
	from_year (int): The start year of the time frame.
	to_year (int): The end year of the time frame.

	Required Parameter = [name,location,from_year,to_year,]

	"""
	return 'Success'

tools = [get_criminal_records]
