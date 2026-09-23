from typing import List, Dict, Any, Union, Tuple, Set 
def get_personality_traits(type:str, traits:List[str]=None) -> str:
	"""
	get_personality_traits : Retrieve the personality traits for a specific personality type, including their strengths and weaknesses.    
	Parameters:
	type (str): The personality type.
	traits (List[str]): List of traits to be retrieved, default is ['strengths'].

	Required Parameter = [type,]

	"""
	return 'Success'

tools = [get_personality_traits]
