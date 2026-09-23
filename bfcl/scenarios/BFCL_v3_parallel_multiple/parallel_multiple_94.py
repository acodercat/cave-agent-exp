from typing import List, Dict, Any, Union, Tuple, Set 
def sort_list(elements:List[int], order:str='asc') -> str:
	"""
	sort_list : Sort the elements of a list in ascending or descending order    
	Parameters:
	elements (List[int]): The list of elements to sort.
	order (str): The order in which to sort the elements. This can be 'asc' for ascending order, or 'desc' for descending order.

	Required Parameter = [elements,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sum_elements(elements:List[int]) -> str:
	"""
	sum_elements : Add all elements of a numeric list    
	Parameters:
	elements (List[int]): The list of numeric elements to add.

	Required Parameter = [elements,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def filter_list(elements:List[str], condition:str) -> str:
	"""
	filter_list : Filters elements of a list based on a given condition    
	Parameters:
	elements (List[str]): The list of elements to filter.
	condition (str): The condition to filter the elements on.

	Required Parameter = [elements,condition,]

	"""
	return 'Success'

tools = [sort_list, sum_elements, filter_list]
