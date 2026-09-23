from typing import List, Dict, Any, Union, Tuple, Set 
def psych_research_get_preference(category:str, option_one:str, option_two:str, demographic:str='all') -> str:
	"""
	psych_research_get_preference : Gathers research data on public preference between two options, based on societal category.    
	Parameters:
	category (str): The societal category the preference data is about. E.g. reading, transportation, food
	option_one (str): The first option people could prefer.
	option_two (str): The second option people could prefer.
	demographic (str): Specific demographic of society to narrow down the research.

	Required Parameter = [category,option_one,option_two,]

	"""
	return 'Success'

tools = [psych_research_get_preference]
