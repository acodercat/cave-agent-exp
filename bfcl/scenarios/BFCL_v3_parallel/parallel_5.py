from typing import List, Dict, Any, Union, Tuple, Set 
def streaming_services_shows_list_and_ratings(streaming_service:str, show_list:List[str], sort_by_rating:bool=None) -> str:
	"""
	streaming_services_shows_list_and_ratings : Get a list of shows and their ratings on specific streaming services.    
	Parameters:
	streaming_service (str): Name of the streaming service. E.g., Netflix, Hulu, etc.
	show_list (List[str]): List of show names to search for on the platform.
	sort_by_rating (bool): If set to true, returns the list sorted by ratings. Defaults to false.

	Required Parameter = [streaming_service,show_list,]

	"""
	return 'Success'

tools = [streaming_services_shows_list_and_ratings]
