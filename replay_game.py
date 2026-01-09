"""
Script to replay a saved chess game.
Usage: python replay_game.py <game_file.json>
"""
import sys
from game_recorder import GameRecorder
from render import Render
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: python replay_game.py <game_file.json>")
        print("Example: python replay_game.py game_replay_20240101_120000.json")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    # Initialize renderer and recorder
    renderer = Render(1000, 600)
    recorder = GameRecorder()
    
    # Replay the game
    try:
        recorder.replay_game(filename, renderer=renderer, delay=1.0)
    except FileNotFoundError:
        print(f"Error: Game file '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error replaying game: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
