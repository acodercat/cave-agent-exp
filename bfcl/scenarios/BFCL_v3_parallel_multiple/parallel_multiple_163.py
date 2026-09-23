from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_calculate_area_circle(radius:int, unit:str=None) -> str:
	"""
	geometry_calculate_area_circle : Calculate the area of a circle given its radius.    
	Parameters:
	radius (int): The radius of the circle.
	unit (str): The measurement unit of the radius (optional parameter, default is 'units').

	Required Parameter = [radius,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_mutual_fund_balance(investment_amount:int, annual_yield:float, years:int) -> str:
	"""
	calculate_mutual_fund_balance : Calculate the final balance of a mutual fund investment based on the total initial investment, annual yield rate and the time period.    
	Parameters:
	investment_amount (int): The initial total amount invested in the fund.
	annual_yield (float): The annual yield rate of the fund.
	years (int): The period of time for the fund to mature.

	Required Parameter = [investment_amount,annual_yield,years,]

	"""
	return 'Success'

tools = [geometry_calculate_area_circle, calculate_mutual_fund_balance]
