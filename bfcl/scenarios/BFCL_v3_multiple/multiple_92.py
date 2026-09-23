from typing import List, Dict, Any, Union, Tuple, Set 
def safeway_vegan_products(location:str, categories:List[str]=None) -> str:
	"""
	safeway_vegan_products : Get available vegan products at specified Safeway store    
	Parameters:
	location (str): City and state where the Safeway store is located, e.g. Denver, CO
	categories (List[str]): Product categories to search within. Default empty array

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def wholefoods_vegan_products(location:str, categories:List[str]=None) -> str:
	"""
	wholefoods_vegan_products : Get available vegan products at specified Whole Foods store    
	Parameters:
	location (str): City and state where the Whole Foods store is located, e.g. Denver, CO
	categories (List[str]): Product categories to search within. Default empty array

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def walmart_vegan_products(location:str, categories:List[str]=None) -> str:
	"""
	walmart_vegan_products : Get available vegan products at specified Walmart store    
	Parameters:
	location (str): City and state where the Walmart store is located, e.g. Denver, CO
	categories (List[str]): Product categories to search within. Default empty array

	Required Parameter = [location,]

	"""
	return 'Success'

tools = [safeway_vegan_products, wholefoods_vegan_products, walmart_vegan_products]
