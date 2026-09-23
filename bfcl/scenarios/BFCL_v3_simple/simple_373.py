from typing import List, Dict, Any, Union, Tuple, Set 
def walmart_purchase(loc:str, product_list:List[str], pack_size:List[int]=None) -> str:
	"""
	walmart_purchase : Retrieve information of items from Walmart including stock availability.    
	Parameters:
	loc (str): Location of the nearest Walmart.
	product_list (List[str]): Items to be purchased listed in an array.
	pack_size (List[int]): Size of the product pack if applicable. The size of the array should be equal to product_list. Default is not use it if not specified.

	Required Parameter = [loc,product_list,]

	"""
	return 'Success'

tools = [walmart_purchase]
