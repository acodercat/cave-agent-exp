from typing import List, Dict, Any, Union, Tuple, Set 
def cosine_similarity_calculate(vector1:List[int], vector2:List[int], rounding:int=None) -> str:
	"""
	cosine_similarity_calculate : Calculate the cosine similarity between two vectors.    
	Parameters:
	vector1 (List[int]): The first vector for calculating cosine similarity.
	vector2 (List[int]): The second vector for calculating cosine similarity.
	rounding (int): Optional: The number of decimals to round off the result. Default 0

	Required Parameter = [vector1,vector2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def correlation_calculate(array1:List[int], array2:List[int], type:str=None) -> str:
	"""
	correlation_calculate : Calculate the correlation coefficient between two arrays of numbers.    
	Parameters:
	array1 (List[int]): The first array of numbers.
	array2 (List[int]): The second array of numbers.
	type (str): Optional: The type of correlation coefficient to calculate. Default is 'pearson'.

	Required Parameter = [array1,array2,]

	"""
	return 'Success'

tools = [cosine_similarity_calculate, correlation_calculate]
