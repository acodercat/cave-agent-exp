from typing import List, Dict, Any, Union, Tuple, Set 
def math_roots_quadratic(a:int, b:int, c:int) -> str:
	"""
	math_roots_quadratic : Calculate the roots of a quadratic equation.    
	Parameters:
	a (int): Coefficient of the second-degree term.
	b (int): Coefficient of the first-degree term.
	c (int): Constant term.

	Required Parameter = [a,b,c,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_roots_cubic(a:float, b:float, c:float, d:float) -> str:
	"""
	math_roots_cubic : Calculate the roots of a cubic equation.    
	Parameters:
	a (float): Coefficient of the third-degree term.
	b (float): Coefficient of the second-degree term.
	c (float): Coefficient of the first-degree term.
	d (float): Constant term.

	Required Parameter = [a,b,c,d,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_roots_polynomial(coefficients:List[float], degree:int=None) -> str:
	"""
	math_roots_polynomial : Calculate the roots of a polynomial equation.    
	Parameters:
	coefficients (List[float]): Array of coefficients of the polynomial equation starting from highest degree term.
	degree (int): Degree of the polynomial equation. Default 0

	Required Parameter = [coefficients,]

	"""
	return 'Success'

tools = [math_roots_quadratic, math_roots_cubic, math_roots_polynomial]
