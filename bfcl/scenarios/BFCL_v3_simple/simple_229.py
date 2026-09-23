from typing import List, Dict, Any, Union, Tuple, Set 
def get_bigfive_scores(characteristics:List[str], scale:str=None) -> str:
	"""
	get_bigfive_scores : Retrieve Big Five Personality trait scores based on individual's behavioural characteristics.    
	Parameters:
	characteristics (List[str]): List of user's behavioural characteristics.
	scale (str): The scoring scale of traits (default is medium).

	Required Parameter = [characteristics,]

	"""
	return 'Success'

tools = [get_bigfive_scores]
