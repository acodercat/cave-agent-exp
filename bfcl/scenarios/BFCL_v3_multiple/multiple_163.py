from typing import List, Dict, Any, Union, Tuple, Set 
def metropolitan_museum_get_top_artworks(number:int, sort_by:str=None) -> str:
	"""
	metropolitan_museum_get_top_artworks : Fetches the list of popular artworks at the Metropolitan Museum of Art. Results can be sorted based on popularity.    
	Parameters:
	number (int): The number of artworks to fetch
	sort_by (str): The criteria to sort the results on. Default is ''.

	Required Parameter = [number,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_search(company:str, start_date:str, location:str, status:str=None) -> str:
	"""
	lawsuit_search : Search for lawsuits related to a specific company within a specific date range and location.    
	Parameters:
	company (str): The company related to the lawsuit.
	start_date (str): Start of the date range for when the lawsuit was filed.
	location (str): Location where the lawsuit was filed.
	status (str): The status of the lawsuit. Default is 'ongoing'.

	Required Parameter = [company,start_date,location,]

	"""
	return 'Success'

tools = [metropolitan_museum_get_top_artworks, lawsuit_search]
