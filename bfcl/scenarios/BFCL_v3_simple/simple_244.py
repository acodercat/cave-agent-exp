from typing import List, Dict, Any, Union, Tuple, Set 
def publication_year_find(author:str, work_title:str, location:str=None) -> str:
	"""
	publication_year_find : Fetches the year a particular scientific work was published.    
	Parameters:
	author (str): Name of the author of the work.
	work_title (str): Title of the scientific work.
	location (str): Place of the publication, if known. Default to 'all'.

	Required Parameter = [author,work_title,]

	"""
	return 'Success'

tools = [publication_year_find]
