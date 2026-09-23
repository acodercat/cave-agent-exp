from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_standard_deviation(gradeDict:Dict[str, Any]) -> str:
	"""
	calculate_standard_deviation : This function calculates the standard deviation across different scores for a specific student.    
	Parameters:
	gradeDict (Dict[str, Any]): A dictionary where keys represent subjects and values represent scores

	Required Parameter = [gradeDict,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_average(gradeDict:Dict[str, Any]) -> str:
	"""
	calculate_average : This function calculates the average grade across different subjects for a specific student.    
	Parameters:
	gradeDict (Dict[str, Any]): A dictionary where keys represent subjects and values represent scores

	Required Parameter = [gradeDict,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def highest_grade(gradeDict:Dict[str, Any]) -> str:
	"""
	highest_grade : This function finds the subject where the student got the highest score.    
	Parameters:
	gradeDict (Dict[str, Any]): A dictionary where keys represent subjects and values represent scores

	Required Parameter = [gradeDict,]

	"""
	return 'Success'

tools = [calculate_standard_deviation, calculate_average, highest_grade]
