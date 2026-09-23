from typing import List, Dict, Any, Union, Tuple, Set 
def run_two_sample_ttest(group1:List[int], group2:List[int], equal_variance:bool=True) -> str:
	"""
	run_two_sample_ttest : Runs a two sample t-test for two given data groups.    
	Parameters:
	group1 (List[int]): First group of data points.
	group2 (List[int]): Second group of data points.
	equal_variance (bool): Assumption about whether the two samples have equal variance.

	Required Parameter = [group1,group2,]

	"""
	return 'Success'

tools = [run_two_sample_ttest]
