from typing import List, Dict, Any, Union, Tuple, Set 
def confidence_interval_calculate(sample_std_dev:int, sample_size:int, sample_mean:int, confidence_level:float=None) -> str:
	"""
	confidence_interval_calculate : Calculate the confidence interval for a mean.    
	Parameters:
	sample_std_dev (int): The standard deviation of the sample.
	sample_size (int): The size of the sample.
	sample_mean (int): The mean of the sample.
	confidence_level (float): The level of confidence. Default is 0.9.

	Required Parameter = [sample_std_dev,sample_size,sample_mean,]

	"""
	return 'Success'

tools = [confidence_interval_calculate]
