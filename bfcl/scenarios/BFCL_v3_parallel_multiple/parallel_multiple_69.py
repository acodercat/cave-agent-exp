from typing import List, Dict, Any, Union, Tuple, Set 
def finance_loan_repayment(loan_amount:float, interest_rate:float, loan_term:int) -> str:
	"""
	finance_loan_repayment : Calculates the monthly repayment for a loan.    
	Parameters:
	loan_amount (float): The amount borrowed or loaned.
	interest_rate (float): The annual interest rate.
	loan_term (int): The term of the loan in years.

	Required Parameter = [loan_amount,interest_rate,loan_term,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def finance_inflation_adjustment(initial_sum:float, years:int, inflation_rate:float) -> str:
	"""
	finance_inflation_adjustment : Adjusts a sum of money for inflation based on the consumer price index (CPI).    
	Parameters:
	initial_sum (float): The initial sum of money.
	years (int): The number of years over which inflation is calculated.
	inflation_rate (float): The annual rate of inflation.

	Required Parameter = [initial_sum,years,inflation_rate,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def finance_property_depreciation(initial_cost:float, depreciation_rate:float, years:int, monthly:bool=False) -> str:
	"""
	finance_property_depreciation : Calculates the depreciated value of a property given its initial cost, depreciation rate, and the number of years.    
	Parameters:
	initial_cost (float): The initial cost of the property.
	depreciation_rate (float): The annual depreciation rate in percentage.
	years (int): The number of years for which to calculate the depreciation.
	monthly (bool): If set to true, it will calculate monthly depreciation instead of annually. (optional)

	Required Parameter = [initial_cost,depreciation_rate,years,]

	"""
	return 'Success'

tools = [finance_loan_repayment, finance_inflation_adjustment, finance_property_depreciation]
