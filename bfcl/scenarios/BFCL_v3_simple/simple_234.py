from typing import List, Dict, Any, Union, Tuple, Set 
def history_eu_fetch_events(century:int, region:str, category:str=None) -> str:
	"""
	history_eu_fetch_events : Fetches significant historical events within a specific time period in European history.    
	Parameters:
	century (int): The century you are interested in.
	region (str): The region of Europe you are interested in.
	category (str): Category of the historical events. Default is 'Culture'.

	Required Parameter = [century,region,]

	"""
	return 'Success'

tools = [history_eu_fetch_events]
