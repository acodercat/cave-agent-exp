from typing import List, Dict, Any, Union, Tuple, Set 
def loan_eligibility_check(financial_institution:str, loan_amount:int, annual_income:int) -> str:
	"""
	loan_eligibility_check : Check for eligibility for a loan given income and loan amount    
	Parameters:
	financial_institution (str): The name of the financial institution e.g. HSBC
	loan_amount (int): The loan amount that is requested
	annual_income (int): Annual income of the applicant

	Required Parameter = [financial_institution,loan_amount,annual_income,]

	"""
	return 'Success'

tools = [loan_eligibility_check]
