from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_cagr(initial_value:int, final_value:int, period_in_years:int) -> str:
	"""
	calculate_cagr : Calculate the Compound Annual Growth Rate (CAGR) given an initial investment value, a final investment value, and the number of years.    
	Parameters:
	initial_value (int): The initial investment value.
	final_value (int): The final investment value.
	period_in_years (int): The period of the investment in years.

	Required Parameter = [initial_value,final_value,period_in_years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_defense_ranking(season:int, top:int=1) -> str:
	"""
	get_defense_ranking : Retrieve the defence ranking of NBA teams in a specified season.    
	Parameters:
	season (int): The NBA season to get defence ranking from.
	top (int): Number of top teams in defence ranking to fetch.

	Required Parameter = [season,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def array_sort(list:List[float], order:str) -> str:
	"""
	array_sort : Sorts a given list in ascending or descending order.    
	Parameters:
	list (List[float]): The list of numbers to be sorted.
	order (str): Order of sorting. If not specified, it will default to ascending.

	Required Parameter = [list,order,]

	"""
	return 'Success'

tools = [calculate_cagr, get_defense_ranking, array_sort]
