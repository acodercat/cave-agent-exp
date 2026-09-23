from typing import List, Dict, Any, Union, Tuple, Set 
def statistics_variance(data:List[int], population:bool=True) -> str:
	"""
	statistics_variance : This function calculates the variance of a given set of numbers.    
	Parameters:
	data (List[int]): The list of data points.
	population (bool): Determines whether to use population variance formula. Default to True

	Required Parameter = [data,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def statistics_median(data:List[int]) -> str:
	"""
	statistics_median : This function returns the median of the data set provided.    
	Parameters:
	data (List[int]): The list of data points.

	Required Parameter = [data,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def statistics_mode(data:List[int]) -> str:
	"""
	statistics_mode : This function determines the mode of a list of numbers.    
	Parameters:
	data (List[int]): The list of data points.

	Required Parameter = [data,]

	"""
	return 'Success'

tools = [statistics_variance, statistics_median, statistics_mode]
