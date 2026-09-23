from typing import List, Dict, Any, Union, Tuple, Set 
def concert_info_get(location:str, date:str, genre:str) -> str:
	"""
	concert_info_get : Retrieve information about concerts based on specific genre, location and date.    
	Parameters:
	location (str): The city where the concert will take place.
	date (str): Time frame to get the concert for.
	genre (str): Genre of the concert.

	Required Parameter = [location,date,genre,]

	"""
	return 'Success'

tools = [concert_info_get]
