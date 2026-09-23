from typing import List, Dict, Any, Union, Tuple, Set 
def get_theater_movie_releases(location:str, timeframe:int, format:str='IMAX') -> str:
	"""
	get_theater_movie_releases : Retrieve the list of movie releases in specific theaters for a specified period.    
	Parameters:
	location (str): The location of the theaters.
	timeframe (int): The number of days for which releases are required from current date.
	format (str): Format of movies - could be 'IMAX', '2D', '3D', '4DX' etc. This is an optional parameter.

	Required Parameter = [location,timeframe,]

	"""
	return 'Success'

tools = [get_theater_movie_releases]
