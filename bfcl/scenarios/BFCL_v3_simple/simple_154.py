from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_future_value(present_value:int, annual_interest_rate:float, years:int, compounds_per_year:int=None) -> str:
	"""
	calculate_future_value : Calculates the future value of an investment based on the present value, interest rate, and time period.    
	Parameters:
	present_value (int): The present value or principal amount.
	annual_interest_rate (float): The annual interest rate in decimal form. Example, 5% is 0.05.
	years (int): The time period in years for which the investment is made.
	compounds_per_year (int): The number of times the interest is compounded per year. Default is 1 (annual compounding).

	Required Parameter = [present_value,annual_interest_rate,years,]

	"""
	return 'Success'

tools = [calculate_future_value]
