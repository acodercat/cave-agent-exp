from typing import List, Dict, Any, Union, Tuple, Set 
def chi_squared_test(table:List[List[int]], alpha:float=None) -> str:
	"""
	chi_squared_test : Performs a Chi-Squared test for independence on a 2x2 contingency table.    
	Parameters:
	table (List[List[int]]): A 2x2 contingency table presented in array form.
	alpha (float): Significance level for the Chi-Squared test. Default is 0.05.

	Required Parameter = [table,]

	"""
	return 'Success'

tools = [chi_squared_test]
