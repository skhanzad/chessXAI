from models import LLMConfig, SwarmConfig
from models import Swarm
from config import LLMType, LLMModel
import chess
from models import Goal
from render import Render
import time

render = Render(1000, 600)
import pygame as pg

swarm = Swarm(SwarmConfig(llm_config=LLMConfig(llm_type=LLMType.OLLAMA, llm_model=LLMModel.LLAMA2, temperature=0.2, base_url="http://127.0.0.1:11434", api_key=None), population_size=2))
board = chess.Board()
goal = Goal("Win the game of chess by making the best moves.")

while not swarm.evolve(board, goal):
    if not render.render(board, reason=goal.reason, move=goal.move, goal=goal.get_description()):
        break
    pg.time.wait(100)

print("Goal achieved!")
print(f"Final board state: {board}")
print(f"Final goal: {goal.get_description()}")
print(f"Final move: {goal.move}")
print(f"Final reason: {goal.reason}")
print(f"Final move made: {goal.move_made}")
print(f"Final achieved: {goal.achieved}")