from typing import List, Dict, Any, Union, Tuple, Set 
def model_DecisionTreeClassifier(criterion:str, max_depth:int, random_state:int) -> str:
	"""
	model_DecisionTreeClassifier : Build a Decision Tree Classifier model with provided criteria    
	Parameters:
	criterion (str): The function to measure the quality of a split, either 'gini' for the Gini impurity or 'entropy' for the information gain.
	max_depth (int): The maximum depth of the tree, specifying how deep the tree can be.
	random_state (int): Controls the randomness of the estimator

	Required Parameter = [criterion,max_depth,random_state,]

	"""
	return 'Success'

tools = [model_DecisionTreeClassifier]
