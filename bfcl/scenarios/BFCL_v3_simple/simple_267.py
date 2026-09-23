from typing import List, Dict, Any, Union, Tuple, Set 
def find_exhibition(location:str, art_form:str, month:str=None, user_ratings:str=None) -> str:
	"""
	find_exhibition : Locate the most popular exhibitions based on criteria like location, time, art form, and user ratings.    
	Parameters:
	location (str): The city and state where the exhibition is held, e.g., New York City, NY.
	art_form (str): The form of art the exhibition is displaying e.g., sculpture.
	month (str): The month of exhibition. Default value will return upcoming events if not specified.
	user_ratings (str): Select exhibitions with user rating threshold. Default is 'low'

	Required Parameter = [location,art_form,]

	"""
	return 'Success'

tools = [find_exhibition]
