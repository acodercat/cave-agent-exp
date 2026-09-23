from typing import List, Dict, Any, Union, Tuple, Set 
def finance_predict_future_value(present_value:int, annual_interest_rate:float, time_years:int, compounding_periods_per_year:int=None) -> str:
	"""
	finance_predict_future_value : Calculate the future value of an investment given its present value, interest rate, the number of compounding periods per year, and the time horizon.    
	Parameters:
	present_value (int): The present value of the investment.
	annual_interest_rate (float): The annual interest rate of the investment.
	compounding_periods_per_year (int): The number of times that interest is compounded per year. Default is 1 (annually).
	time_years (int): The investment horizon in years.

	Required Parameter = [present_value,annual_interest_rate,time_years,]

	"""
	return 'Success'

tools = [finance_predict_future_value]
