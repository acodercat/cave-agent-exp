from typing import List, Dict, Any, Union, Tuple, Set 
def chess_play(moves:List[str]) -> str:
	"""
	chess_play : Makes moves in a chess game.    
	Parameters:
	moves (List[str]): List of moves to play in the game.

	Required Parameter = [moves,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def game_of_life_play(rounds:int, start_board:List[int]) -> str:
	"""
	game_of_life_play : Runs a round of game of life based on provided board.    
	Parameters:
	rounds (int): Number of rounds to play.
	start_board (List[int]): Starting board of game, leave empty for random starting point.

	Required Parameter = [rounds,start_board,]

	"""
	return 'Success'

tools = [chess_play, game_of_life_play]
