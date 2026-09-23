from typing import List, Dict, Any, Union, Tuple, Set 
def employee_fetch_data(company_name:str, employee_id:int, data_field:List[str]=['Personal Info']) -> str:
	"""
	employee_fetch_data : Fetches the detailed data for a specific employee in a given company.    
	Parameters:
	company_name (str): The name of the company.
	employee_id (int): The unique ID of the employee.
	data_field (List[str]): Fields of data to be fetched for the employee (Optional).

	Required Parameter = [company_name,employee_id,]

	"""
	return 'Success'

tools = [employee_fetch_data]
