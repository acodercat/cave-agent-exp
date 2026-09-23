from typing import List, Dict, Any, Union, Tuple, Set 
def sculpture_get_details(artist:str, title:str, detail:str=None) -> str:
	"""
	sculpture_get_details : Retrieve details of a sculpture based on the artist and the title of the sculpture.    
	Parameters:
	artist (str): The artist who made the sculpture.
	title (str): The title of the sculpture.
	detail (str): The specific detail wanted about the sculpture. Default is 'general information'.

	Required Parameter = [artist,title,]

	"""
	return 'Success'

tools = [sculpture_get_details]
