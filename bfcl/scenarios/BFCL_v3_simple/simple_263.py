from typing import List, Dict, Any, Union, Tuple, Set 
def get_sculpture_info(artist_name:str, detail:bool=None) -> str:
	"""
	get_sculpture_info : Retrieves the most recent artwork by a specified artist with its detailed description.    
	Parameters:
	artist_name (str): The name of the artist.
	detail (bool): If True, it provides detailed description of the sculpture. Defaults to False.

	Required Parameter = [artist_name,]

	"""
	return 'Success'

tools = [get_sculpture_info]
