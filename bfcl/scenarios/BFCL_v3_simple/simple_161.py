from typing import List, Dict, Any, Union, Tuple, Set 
def crime_statute_lookup(jurisdiction:str, crime:str, detail_level:str=None) -> str:
	"""
	crime_statute_lookup : Look up the criminal statutes in a specific jurisdiction to find possible punishments for a specific crime.    
	Parameters:
	jurisdiction (str): The jurisdiction to search in, usually a state or country.
	crime (str): The crime to search for.
	detail_level (str): How detailed of a report to return. Optional, default is 'basic'.

	Required Parameter = [jurisdiction,crime,]

	"""
	return 'Success'

tools = [crime_statute_lookup]
