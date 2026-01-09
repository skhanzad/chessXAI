from models import LLMConfig, LLM
from config import LLMType
import chess
from models import Goal
from render import Render
import time
import chess.engine
import os
import pygame as pg
from dotenv import load_dotenv
from game_recorder import GameRecorder
from plan_dag import PlanDAG, PlanType

load_dotenv()

ENGINE_PATH = os.path.join(os.path.dirname(__file__), "engine", "stockfish", "stockfish.exe")

# ============================================================================
# CONFIGURATION: Choose who plays first
# ============================================================================
# Set to True if Agent plays first (as White), False if Stockfish plays first (as White)
AGENT_PLAYS_FIRST = True  # Change to True to have Agent play first
# ============================================================================

# Initialize Stockfish engine
try:
    stockfish = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    print("Stockfish engine initialized successfully")
except Exception as e:
    print(f"Error initializing Stockfish: {e}")
    print("Make sure Stockfish is installed at the correct path.")
    exit(1)

# Initialize Agent (single LLM agent)
agent = LLM(LLMConfig(
    llm_type=LLMType.OPENAI,
    llm_model="gpt-5.1",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.2
))
goal = Goal("Win the game of chess by making the best moves against Stockfish.")

# Initialize board and renderer
board = chess.Board()
render = Render(1000, 600)

# Initialize game recorder
recorder = GameRecorder()
recorder.set_metadata(agent_plays_first=AGENT_PLAYS_FIRST)

# Initialize Plan DAG for strategic planning
plan_dag = PlanDAG()

# Determine which color each player gets
if AGENT_PLAYS_FIRST:
    agent_color = chess.WHITE
    stockfish_color = chess.BLACK
    agent_color_str = "White"
    stockfish_color_str = "Black"
else:
    agent_color = chess.BLACK
    stockfish_color = chess.WHITE
    agent_color_str = "Black"
    stockfish_color_str = "White"

print("\n=== Stockfish vs Agent Game ===")
if AGENT_PLAYS_FIRST:
    print("Agent plays as White, Stockfish plays as Black")
else:
    print("Stockfish plays as White, Agent plays as Black")
print("Starting game...\n")

# Main game loop
running = True
move_number = 0

while not board.is_game_over() and running:
    move_number += 1
    current_turn = "White" if board.turn == chess.WHITE else "Black"
    
    print(f"\n--- Move {move_number}: {current_turn}'s turn ---")
    
    try:
        player_name = None  # Track who made the move
        board_before_move = board.copy()  # Save board state before move
        result = None  # Store Stockfish result
        
        if board.turn == agent_color:
            # Agent's turn
            print(f"Agent is thinking ({agent_color_str})...")
            
            # Let the agent make a move
            agent.evolve(board, goal, plan_dag=plan_dag, move_number=move_number)
            
            if goal.move_made and goal.move:
                move_uci = goal.move.uci()
                reason_str = goal.reason if goal.reason else "Agent's strategic move"
                player_name = "Agent"
                print(f"Agent ({agent_color_str}) played: {move_uci}")
                print(f"Reason: {reason_str}")
            else:
                print(f"Agent ({agent_color_str}) failed to make a move!")
                move_uci = None
                reason_str = "Agent failed to generate a valid move"
        
        else:
            # Stockfish's turn
            print(f"Stockfish is thinking ({stockfish_color_str})...")
            result = stockfish.play(board, chess.engine.Limit(time=1.0))
            move_uci = result.move.uci() if result.move else None
            
            # Convert result.info to string if it exists
            reason_str = None
            if hasattr(result, 'info') and result.info:
                if isinstance(result.info, dict):
                    info_parts = []
                    if 'score' in result.info:
                        score = result.info['score']
                        if hasattr(score, 'relative'):
                            info_parts.append(f"Score: {score.relative}")
                    if 'depth' in result.info:
                        info_parts.append(f"Depth: {result.info['depth']}")
                    if 'pv' in result.info:
                        pv = result.info['pv']
                        if isinstance(pv, list) and len(pv) > 0:
                            info_parts.append(f"PV: {pv[0].uci() if hasattr(pv[0], 'uci') else str(pv[0])}")
                    reason_str = "; ".join(info_parts) if info_parts else "Stockfish analysis"
                else:
                    reason_str = str(result.info)
            else:
                reason_str = f"Stockfish move: {move_uci}"
            
            # Apply Stockfish's move
            if result.move:
                board.push(result.move)
                player_name = "Stockfish"
                print(f"Stockfish ({stockfish_color_str}) played: {move_uci}")
                
                # Create a plan node for Stockfish move (engine optimization plan)
                stockfish_plan_id = plan_dag.create_plan(
                    plan_type=PlanType.POSITIONAL_IMPROVEMENT,
                    description="Stockfish engine optimization",
                    parent_id=None,
                    move_number=move_number
                )
                plan_dag.add_move_to_plan(move_uci, stockfish_plan_id)
                goal.plan_node = plan_dag.get_plan_path_for_move(move_uci)
        
        # Record the move with detailed information
        if move_uci and player_name:
            # Extract evaluation and intent information
            evaluation_engine = None
            intent_type = "strategic"
            intent_description = reason_str or ""
            assumptions = []
            threats_created = []
            risks_accepted = []
            expected_responses = []
            evaluation_self = None
            
            if player_name == "Stockfish":
                # Extract evaluation from Stockfish info
                if result and hasattr(result, 'info') and result.info and isinstance(result.info, dict):
                    if 'score' in result.info:
                        score = result.info['score']
                        if hasattr(score, 'relative'):
                            evaluation_engine = str(score.relative)
                    intent_type = "engine_move"
                    intent_description = reason_str or "Stockfish engine move"
            else:
                # Agent move - extract from reason/goal
                intent_description = reason_str or goal.get_description() or ""
                # Try to infer intent type from description
                desc_lower = intent_description.lower()
                if "attack" in desc_lower or "threat" in desc_lower:
                    intent_type = "tactical"
                elif "defense" in desc_lower or "protect" in desc_lower:
                    intent_type = "defensive"
                elif "develop" in desc_lower or "castl" in desc_lower:
                    intent_type = "development"
                elif "break" in desc_lower or "open" in desc_lower:
                    intent_type = "strategic_break"
                else:
                    intent_type = "strategic"
            
            # Get plan_node from goal if available
            plan_node = getattr(goal, 'plan_node', None)
            
            # Use board before move for descriptive format conversion
            recorder.record_move(
                move_number=move_number,
                actor=player_name if player_name == "Stockfish" else "GPT-5.1",  # Use model name for agent
                move_uci=move_uci,
                board=board_before_move,
                position_fen=board.fen(),
                intent_type=intent_type,
                intent_description=intent_description,
                assumptions=assumptions,
                threats_created=threats_created,
                risks_accepted=risks_accepted,
                expected_responses=expected_responses,
                evaluation_self=evaluation_self,
                evaluation_engine=evaluation_engine,
                plan_node=plan_node
            )
        
        # Render the board after each move
        goal_description = goal.get_description()
        if not render.render(board, reason=reason_str, move=move_uci, goal=goal_description):
            running = False
            break
        
        pg.time.wait(100) # Delay for visualization
        
        # Check game status
        if board.is_checkmate():
            winner = "Black" if board.turn == chess.WHITE else "White"
            print(f"\n{'='*50}")
            print(f"CHECKMATE! {winner} wins!")
            print(f"{'='*50}")
        elif board.is_stalemate():
            print(f"\n{'='*50}")
            print("STALEMATE! Game is a draw.")
            print(f"{'='*50}")
        elif board.is_insufficient_material():
            print(f"\n{'='*50}")
            print("INSUFFICIENT MATERIAL! Game is a draw.")
            print(f"{'='*50}")
        elif board.is_seventyfive_moves():
            print(f"\n{'='*50}")
            print("75-MOVE RULE! Game is a draw.")
            print(f"{'='*50}")
        elif board.is_fivefold_repetition():
            print(f"\n{'='*50}")
            print("FIVEFOLD REPETITION! Game is a draw.")
            print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error during game loop: {e}")
        import traceback
        traceback.print_exc()
        break

# Final render
if board.is_game_over():
    result = board.result()
    print(f"\nFinal game result: {result}")
    recorder.set_metadata(agent_plays_first=AGENT_PLAYS_FIRST, final_result=result)
    render.render(board, reason=f"Game Over: {result}", move=None, goal=goal.get_description())
    time.sleep(3)  # Show final position

# Save the game
try:
    saved_filename = recorder.save_game(plan_dag=plan_dag)
    print(f"\nGame saved to: {saved_filename}")
    print(f"Plan DAG structure saved with {len(plan_dag.nodes)} plan nodes")
except Exception as e:
    print(f"\nError saving game: {e}")

# Clean up
try:
    stockfish.quit()
    print("\nStockfish engine closed.")
except Exception:
    pass

# Game finished
print("\nGame finished.")
