from typing import List, Dict, Any, Union, Tuple, Set 
def finance_calculator_npv(cash_flows:List[int], discount_rate:float, years:List[int]=None) -> str:
	"""
	finance_calculator_npv : Calculate the Net Present Value (NPV) for a series of cash flows discounted at a certain interest rate.    
	Parameters:
	cash_flows (List[int]): A list of cash flows.
	discount_rate (float): The annual interest rate used to discount the cash flows.
	years (List[int]): A list of years when the cash flow occurs. Default is empty array.

	Required Parameter = [cash_flows,discount_rate,]

	"""
	return 'Success'

tools = [finance_calculator_npv]
