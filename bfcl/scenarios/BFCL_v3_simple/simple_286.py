from typing import List, Dict, Any, Union, Tuple, Set 
def concert_get_details(artist:str, location:str, date:str=None) -> str:
	"""
	concert_get_details : Fetch the details for a particular concert based on the artist and location.    
	Parameters:
	artist (str): Name of the artist/band who's performing.
	location (str): City where the concert is taking place.
	date (str): Date of the concert in 'mm-yyyy' format. Default is the current month if not specified.

	Required Parameter = [artist,location,]

	"""
	return 'Success'

tools = [concert_get_details]
