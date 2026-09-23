from typing import List, Dict, Any, Union, Tuple, Set 
def solve_quadratic_equation(a:int, b:int, c:int) -> str:
	"""
	solve_quadratic_equation : Function solves the quadratic equation and returns its roots.    
	Parameters:
	a (int): Coefficient of x squared
	b (int): Coefficient of x
	c (int): Constant term in the quadratic equation

	Required Parameter = [a,b,c,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def portfolio_future_value(stock:str, invested_amount:int, expected_annual_return:float, years:int) -> str:
	"""
	portfolio_future_value : Calculate the future value of an investment in a specific stock based on the invested amount, expected annual return and number of years.    
	Parameters:
	stock (str): The ticker symbol of the stock.
	invested_amount (int): The invested amount in USD.
	expected_annual_return (float): The expected annual return on investment as a decimal. E.g. 5% = 0.05
	years (int): The number of years for which the investment is made.

	Required Parameter = [stock,invested_amount,expected_annual_return,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_info(company_name:str, detail_level:str, market:str=None) -> str:
	"""
	get_stock_info : Retrieves information about a specific stock based on company's name.    
	Parameters:
	company_name (str): The name of the company.
	detail_level (str): Level of detail for stock information. Can be 'summary' or 'detailed'.
	market (str): The stock market of interest. Default is 'NASDAQ'

	Required Parameter = [company_name,detail_level,]

	"""
	return 'Success'

tools = [solve_quadratic_equation, portfolio_future_value, get_stock_info]
