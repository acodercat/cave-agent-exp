from typing import List, Dict, Any, Union, Tuple, Set 
def concert_search(genre:str, location:str, date:str, price_range:str=None) -> str:
	"""
	concert_search : Locate a concert based on specific criteria like genre, location, and date.    
	Parameters:
	genre (str): Genre of the concert.
	location (str): City of the concert.
	date (str): Date of the concert, e.g. this weekend, today, tomorrow.
	price_range (str): Expected price range of the concert tickets. Default is 'free'.

	Required Parameter = [genre,location,date,]

	"""
	return 'Success'

tools = [concert_search]
