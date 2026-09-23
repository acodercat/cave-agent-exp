from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_lcm(num1:int, num2:int, method:str='standard') -> str:
	"""
	calculate_lcm : Calculate the least common multiple (lcm) between two integers.    
	Parameters:
	num1 (int): First number to calculate lcm for.
	num2 (int): Second number to calculate lcm for.
	method (str): The specific method to use in the calculation. Supported values: 'standard', 'reduced'

	Required Parameter = [num1,num2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_gcd(num1:int, num2:int, algorithm:str='euclidean') -> str:
	"""
	calculate_gcd : Calculate the greatest common divisor (gcd) between two integers.    
	Parameters:
	num1 (int): First number to calculate gcd for.
	num2 (int): Second number to calculate gcd for.
	algorithm (str): The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'

	Required Parameter = [num1,num2,]

	"""
	return 'Success'

tools = [calculate_lcm, calculate_gcd]
