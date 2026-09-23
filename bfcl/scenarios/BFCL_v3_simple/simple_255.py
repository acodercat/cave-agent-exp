from typing import List, Dict, Any, Union, Tuple, Set 
def religious_history_get_papal_biography(papal_name:str, include_contributions:bool) -> str:
	"""
	religious_history_get_papal_biography : Retrieve the biography and main religious and historical contributions of a Pope based on his papal name.    
	Parameters:
	papal_name (str): The papal name of the Pope.
	include_contributions (bool): Include main contributions of the Pope in the response if true.

	Required Parameter = [papal_name,include_contributions,]

	"""
	return 'Success'

tools = [religious_history_get_papal_biography]
