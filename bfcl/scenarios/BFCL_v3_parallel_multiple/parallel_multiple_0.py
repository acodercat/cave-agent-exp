from typing import List, Dict, Any, Union, Tuple, Set 
def math_toolkit_sum_of_multiples(lower_limit:int, upper_limit:int, multiples:List[int]) -> str:
	"""
	math_toolkit_sum_of_multiples : Find the sum of all multiples of specified numbers within a specified range.    
	Parameters:
	lower_limit (int): The start of the range (inclusive).
	upper_limit (int): The end of the range (inclusive).
	multiples (List[int]): The numbers to find multiples of.

	Required Parameter = [lower_limit,upper_limit,multiples,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_toolkit_product_of_primes(count:int) -> str:
	"""
	math_toolkit_product_of_primes : Find the product of the first n prime numbers.    
	Parameters:
	count (int): The number of prime numbers to multiply together.

	Required Parameter = [count,]

	"""
	return 'Success'

tools = [math_toolkit_sum_of_multiples, math_toolkit_product_of_primes]
