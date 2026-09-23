from typing import List, Dict, Any, Union, Tuple, Set 
def math_sqrt(num:float, accuracy:float=2.0) -> str:
	"""
	math_sqrt : Calculates the square root of a number.    
	Parameters:
	num (float): The number.
	accuracy (float): The number of decimal places in the result.

	Required Parameter = [num,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_gcd(num1:int, num2:int) -> str:
	"""
	math_gcd : Calculates the greatest common divisor of two numbers.    
	Parameters:
	num1 (int): The first number.
	num2 (int): The second number.

	Required Parameter = [num1,num2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_lcm(num1:int, num2:int) -> str:
	"""
	math_lcm : Calculates the least common multiple of two numbers.    
	Parameters:
	num1 (int): The first number.
	num2 (int): The second number.

	Required Parameter = [num1,num2,]

	"""
	return 'Success'

tools = [math_sqrt, math_gcd, math_lcm]
