from typing import List, Dict, Any, Union, Tuple, Set 
def imdb_find_movies_by_actor(actor_name:str, year:int, category:str=None) -> str:
	"""
	imdb_find_movies_by_actor : Searches the database to find all movies by a specific actor within a certain year.    
	Parameters:
	actor_name (str): The name of the actor.
	year (int): The specific year to search in.
	category (str): The category of the film (e.g. Drama, Comedy, etc). Default is 'all'

	Required Parameter = [actor_name,year,]

	"""
	return 'Success'

tools = [imdb_find_movies_by_actor]
