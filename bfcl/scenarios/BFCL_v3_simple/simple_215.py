from typing import List, Dict, Any, Union, Tuple, Set 
def movie_details_brief(title:str, extra_info:bool='false') -> str:
	"""
	movie_details_brief : This function retrieves a brief about a specified movie.    
	Parameters:
	title (str): Title of the movie
	extra_info (bool): Option to get additional information like Director, Cast, Awards etc.

	Required Parameter = [title,]

	"""
	return 'Success'

tools = [movie_details_brief]
