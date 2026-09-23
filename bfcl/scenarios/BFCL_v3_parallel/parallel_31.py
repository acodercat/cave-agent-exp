from typing import List, Dict, Any, Union, Tuple, Set 
def history_fact_fetch(event:str, depth:str='detailed', year:int=None) -> str:
	"""
	history_fact_fetch : Retrieve facts about historical events or documents    
	Parameters:
	event (str): The historical event or document you want to know about.
	depth (str): The depth of information required. Choices are 'brief' or 'detailed'.
	year (int): The year of the event/document. default is 0

	Required Parameter = [event,]

	"""
	return 'Success'

tools = [history_fact_fetch]
