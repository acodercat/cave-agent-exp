from typing import List, Dict, Any, Union, Tuple, Set 
def museum_exhibition_detail(exhibition_name:str, museum_name:str, visitor_type:List[str]=None) -> str:
	"""
	museum_exhibition_detail : Provides details of a particular exhibition in a museum, including the cost per visit for different age groups.    
	Parameters:
	exhibition_name (str): The name of the exhibition.
	museum_name (str): The name of the museum.
	visitor_type (List[str]): Age group of the visitor. Default is: ['adult']

	Required Parameter = [exhibition_name,museum_name,]

	"""
	return 'Success'

tools = [museum_exhibition_detail]
