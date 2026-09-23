from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_compound_interest(principle:int, interest_rate:float, time:int, compounds_per_year:int=None) -> str:
	"""
	calculate_compound_interest : Calculates the compound interest of an investment over a given time period.    
	Parameters:
	principle (int): The initial amount of the investment.
	interest_rate (float): The yearly interest rate of the investment.
	time (int): The time, in years, the money is invested or borrowed for.
	compounds_per_year (int): The number of times the interest is compounded per year. Default is 1 (interest is compounded yearly).

	Required Parameter = [principle,interest_rate,time,]

	"""
	return 'Success'

tools = [calculate_compound_interest]
