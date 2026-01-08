from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from config import LLMConfig, SwarmConfig, LLMType

import chess

from pydantic import BaseModel, Field

GoalPrompt = PromptTemplate(
    input_variables=["board", "goal", "format_instructions", "turn", "legal_moves"],
    template="""
    You are a chess agent.
    You are given a goal to solve.
    You need to solve the goal by making a move on the chess board.
    
    Goal: {goal}
    
    The chess board is given below (FEN notation):
    {board}
    
    CRITICAL: It is currently {turn}'s turn to move.
    
    IMPORTANT: The board state has changed since the last move. Previous moves are no longer available.
    You MUST look at the CURRENT board state and legal moves list below.
    
    ================================================================================
    AVAILABLE LEGAL MOVES FOR {turn} (UCI NOTATION) - YOU MUST CHOOSE ONE OF THESE:
    ================================================================================
    {legal_moves}
    ================================================================================
    
    CRITICAL RULES - READ CAREFULLY:
    1. You MUST select EXACTLY ONE move from the list above.
    2. The move you choose MUST appear EXACTLY as shown in the list above.
    3. Copy the move character-for-character (e.g., if list shows "g1f3", use "g1f3").
    4. Do NOT modify, abbreviate, or change the move in any way.
    5. Do NOT create new moves - only use moves from the list.
    6. Do NOT use algebraic notation (like "e4" or "Nf3") - only UCI notation.
    7. If the move is not in the list above, it is INVALID and will be rejected.
    8. The system will ONLY accept moves that appear in the list above.
    
    VALIDATION: Before responding, verify your chosen move appears in the list above.
    If it does not appear, choose a different move from the list.
    
    Examples of UCI notation format:
    - "e2e4" means pawn moves from e2 to e4
    - "g1f3" means knight moves from g1 to f3
    - "e1g1" means king castles kingside (e1 to g1)
    
    Provide the move and explain your reasoning.
    
    {format_instructions}
    """
)

class Output(BaseModel):
    move: str = Field(description="The move to make in UCI notation. MUST be exactly one of the legal moves provided in the prompt. Copy it exactly as it appears in the legal moves list (e.g., 'e2e4', 'g1f3').")
    reason: str = Field(description="The reason for the move")
    new_goal: str = Field(description="The new goal to solve")


class Goal:
    def __init__(self, description: str):
        self.original_description = description
        self.description = description
        self.achieved = False
        self.move = None
        self.reason = None
        self.move_made = False  # Track if a valid move was made

    def achieve(self, board: chess.Board, move_str: str, reason: str):
        """
        Attempt to achieve the goal by making a move.
        Only valid moves for the current player are accepted.
        """
        self.reason = reason
        self.move = None
        self.move_made = False
        
        # Store whose turn it is before the move
        current_turn = "White" if board.turn == chess.WHITE else "Black"
        expected_color = board.turn  # Store expected color
        moves_before = len(board.move_stack)
        
        # Validate board is in a playable state
        if board.is_game_over():
            print(f"    Game is over, cannot make move")
            self.achieved = False
            self.move_made = False
            return
        
        # IMMEDIATE VALIDATION: Check if move is in legal moves before parsing
        move_str_clean = move_str.strip()
        legal_moves_uci_precheck = [m.uci() for m in list(board.legal_moves)]
        
        if move_str_clean not in legal_moves_uci_precheck:
            print(f"    REJECTED: Move '{move_str_clean}' is NOT in legal moves list!")
            print(f"    Legal moves count: {len(legal_moves_uci_precheck)}")
            self.achieved = False
            self.move_made = False
            return
        
        # Move is in legal moves list - proceed with parsing
        # Try UCI notation first
        try:
            self.move = chess.Move.from_uci(move_str_clean)
        except ValueError:
            # If UCI fails, try Standard Algebraic Notation (SAN)
            try:
                self.move = board.parse_san(move_str_clean)
            except ValueError:
                # Both failed - invalid move notation (even though it was in the list)
                print(f"    ERROR: Invalid move notation: '{move_str_clean}' (was in legal moves list)")
                self.achieved = False
                self.move_made = False
                return
        
        # Validate and apply the move
        # Convert legal_moves to list for reliable membership testing
        legal_moves_list = list(board.legal_moves)
        
        if self.move is None:
            self.achieved = False
            self.move_made = False
            return
        
        # CRITICAL: Verify board turn hasn't changed
        if board.turn != expected_color:
            print(f"    ERROR: Board turn changed during move processing!")
            self.achieved = False
            self.move_made = False
            return
        
        # Check if move is legal (this also ensures it's for the correct player)
        if self.move in legal_moves_list:
            # Push the move to the board
            try:
                board.push(self.move)
                self.move_made = True
                
                # Verify the move was actually applied
                moves_after = len(board.move_stack)
                if moves_after > moves_before:
                    # Move was successfully applied
                    # CRITICAL: Verify turn alternated (White -> Black or Black -> White)
                    if board.turn == expected_color:
                        print(f"    ERROR: Turn did not alternate after move!")
                        self.achieved = False
                        self.move_made = False
                        board.pop()  # Undo the move since turn didn't alternate
                        return
                    
                    # Move was successfully applied and turn alternated
                    if board.is_checkmate():
                        self.achieved = True
                    else:
                        self.achieved = False
                else:
                    # Something went wrong - move wasn't applied
                    # This shouldn't happen, but handle it just in case
                    print(f"    ERROR: Move pushed but move_stack didn't increase!")
                    self.achieved = False
                    self.move_made = False
            except Exception as e:
                print(f"    ERROR pushing move to board: {e}")
                self.achieved = False
                self.move_made = False
        else:
            # Invalid move - don't push it
            attempted_uci = self.move.uci() if self.move else move_str
            legal_moves_uci = [m.uci() for m in legal_moves_list]
            if attempted_uci not in legal_moves_uci:
                # Move is not in legal moves - this is the problem
                print(f"    Move '{attempted_uci}' not in legal moves (total: {len(legal_moves_list)})")
            self.achieved = False
            self.move_made = False
    
    def is_achieved(self):
        return self.achieved

    def get_description(self):
        # Return the current goal description (which may have been updated)
        # If description was updated, use it; otherwise use original
        if self.description != self.original_description:
            return self.description
        return self.original_description


class LLM:

    def __init__(self, config: LLMConfig):
        if config.llm_type == LLMType.OLLAMA:
            self.llm = ChatOllama(
                model=config.llm_model.value,
                temperature=config.temperature,
                base_url=config.base_url,
                api_key=config.api_key
            )
        elif config.llm_type == LLMType.OPENAI:
            self.llm = ChatOpenAI(
                model=config.llm_model.value,
                temperature=config.temperature,
                api_key=config.api_key
            )
        elif config.llm_type == LLMType.ANTHROPIC:
            self.llm = ChatAnthropic(
                model=config.llm_model.value,
                temperature=config.temperature,
                api_key=config.api_key
            )

    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    def evolve(self, board: chess.Board = None, goal: Goal = None):
        """
        Evolve the agent based on the goal to solve.
        Ensures only valid moves are chosen and moves are made in the correct turn.
        """
        parser = PydanticOutputParser(pydantic_object=Output)
        chain = GoalPrompt | self.llm | parser
        
        # Determine whose turn it is - CRITICAL: only make moves for the current player
        turn = "White" if board.turn == chess.WHITE else "Black"
        expected_color = board.turn  # Store expected color to verify later
        
        # Get list of legal moves in UCI notation
        # Show all moves if there are 40 or fewer, otherwise show first 40
        all_legal_moves = list(board.legal_moves)
        if len(all_legal_moves) == 0:
            legal_moves_str = "No legal moves available - game may be over"
        elif len(all_legal_moves) <= 40:
            # Show all moves if reasonable number
            legal_moves = [move.uci() for move in all_legal_moves]
            legal_moves_str = ", ".join(legal_moves)
        else:
            # Show first 40 moves
            legal_moves = [move.uci() for move in all_legal_moves[:40]]
            legal_moves_str = ", ".join(legal_moves)
            legal_moves_str += f" (and {len(all_legal_moves) - 40} more - choose from first 40)"
        
        try:
            result = chain.invoke({
                "board": board.fen(), 
                "goal": goal.get_description(),
                "turn": turn,
                "legal_moves": legal_moves_str,
                "format_instructions": parser.get_format_instructions()
            })
        except Exception as e:
            print(f"  Error getting move from LLM: {e}")
            return False
        
        # CRITICAL: Verify board state hasn't changed (another agent might have moved)
        if board.turn != expected_color:
            print(f"  ERROR: Board turn changed before move validation! Expected {expected_color}, got {board.turn}")
            return False
        
        # Get fresh legal moves list - only contains moves for current player
        legal_moves_uci = [m.uci() for m in list(board.legal_moves)]
        
        # Extract and validate the move immediately
        attempted_move_str = result.move.strip() if hasattr(result, 'move') and result.move else None
        
        # IMMEDIATE VALIDATION: Reject any move not in legal moves list
        # This ensures we ONLY accept valid moves
        if not attempted_move_str:
            print(f"  REJECTED: No move generated by LLM")
            if len(all_legal_moves) > 0:
                fallback_move = all_legal_moves[0].uci()
                attempted_move_str = fallback_move
                result.move = fallback_move
                result.reason = "Fallback: No move was generated"
                print(f"  Using fallback move: {fallback_move}")
            else:
                print(f"  ERROR: No legal moves available!")
                return False
        elif attempted_move_str not in legal_moves_uci:
            # IMMEDIATE REJECTION: Move is not in legal moves list
            print(f"  REJECTED: Generated move '{attempted_move_str}' is NOT in legal moves list!")
            print(f"  Legal moves available: {len(legal_moves_uci)} moves")
            print(f"  First 10 legal moves: {legal_moves_uci[:10]}")
            
            # Force fallback to a valid move
            if len(all_legal_moves) > 0:
                fallback_move = all_legal_moves[0].uci()
                print(f"  FORCING fallback: selecting valid move '{fallback_move}'")
                original_move = attempted_move_str
                attempted_move_str = fallback_move
                result.move = fallback_move
                original_reason = result.reason if hasattr(result, 'reason') and result.reason else "No reason provided"
                result.reason = f"Invalid move '{original_move}' rejected - using fallback '{fallback_move}'. Original reason: {original_reason}"
            else:
                print(f"  ERROR: No legal moves available!")
                return False
        else:
            # Move is valid - confirm it
            print(f"  VALIDATED: Move '{attempted_move_str}' is in legal moves list ✓")
        
        # Try to achieve the move - use attempted_move_str which may have been updated to fallback
        moves_before_achieve = len(board.move_stack)
        move_to_apply = attempted_move_str if attempted_move_str else (result.move if hasattr(result, 'move') else None)
        reason_to_use = result.reason if hasattr(result, 'reason') and result.reason else "No reason provided"
        
        # FINAL VALIDATION: Ensure move is in legal moves and turn is correct
        # Refresh legal moves list in case board state changed
        if board.turn != expected_color:
            print(f"  ERROR: Board turn changed! Expected {expected_color}, got {board.turn}")
            return False
        
        current_legal_moves = [m.uci() for m in list(board.legal_moves)]
        
        # Ensure we have a move to apply
        if not move_to_apply:
            print(f"  ERROR: No move to apply!")
            if len(current_legal_moves) > 0:
                move_to_apply = current_legal_moves[0]
                print(f"  Using emergency fallback: {move_to_apply}")
            else:
                return False
        
        # CRITICAL: Final validation - move MUST be in current legal moves
        if move_to_apply not in current_legal_moves:
            print(f"  ERROR: Move '{move_to_apply}' NOT in current legal moves - REJECTING!")
            # Force use of a valid move from current list
            if len(current_legal_moves) > 0:
                move_to_apply = current_legal_moves[0]
                print(f"  FORCING valid move from current list: {move_to_apply}")
            else:
                print(f"  ERROR: No legal moves available!")
                return False
        
        # CRITICAL: Final validation - ensure move object is valid and legal
        try:
            move_obj = chess.Move.from_uci(move_to_apply)
            if move_obj not in board.legal_moves:
                print(f"  ERROR: Move '{move_to_apply}' is not a legal move object!")
                # Force use of first legal move
                if len(current_legal_moves) > 0:
                    move_to_apply = current_legal_moves[0]
                    move_obj = chess.Move.from_uci(move_to_apply)
                    print(f"  FORCING valid move object: {move_to_apply}")
                else:
                    return False
            # Verify move is for the correct player
            if board.turn != expected_color:
                print(f"  ERROR: Turn mismatch! Expected {expected_color}, got {board.turn}")
                return False
        except ValueError as e:
            print(f"  ERROR: Invalid move format '{move_to_apply}': {e}")
            # Force use of first legal move
            if len(current_legal_moves) > 0:
                move_to_apply = current_legal_moves[0]
                print(f"  FORCING valid move format: {move_to_apply}")
            else:
                return False
        
        # Final confirmation
        if move_to_apply not in current_legal_moves:
            print(f"  FATAL ERROR: Move '{move_to_apply}' still not valid after all checks!")
            return False
        
        # Now apply the move
        print(f"  Applying move: {move_to_apply} (for {turn})")
        goal.achieve(board, move_to_apply, reason_to_use)
        
        moves_after_achieve = len(board.move_stack)
        
        # Verify board was updated
        if goal.move_made:
            if moves_after_achieve > moves_before_achieve:
                # Success - move was applied
                pass
            else:
                # Something went wrong - move was marked as made but board wasn't updated
                print(f"  ERROR: Move marked as made but board not updated!")
                goal.move_made = False
        else:
            print(f"  Move was not made - goal.move_made is False")
        
        # Update goal description if provided and valid
        if result.new_goal and result.new_goal.strip():
            goal.description = result.new_goal
        
        return goal.is_achieved()


class Swarm:
    def __init__(self, config: SwarmConfig):
        self.swarm = [LLM(config.llm_config) for _ in range(config.population_size)]
        self.config = config
    
    def evolve(self, board: chess.Board = None, goal: Goal = None) -> bool:
        """
        Each agent makes a move in sequence. Moves must alternate between White and Black.
        Only valid moves are accepted.
        """
        # Each agent makes a move in sequence, board updates after each move
        for i, agent in enumerate(self.swarm):
            # Check if goal is already achieved before this agent's turn
            if goal.is_achieved():
                return True
            
            # Store board state before this agent's move
            moves_before = len(board.move_stack)
            turn_before = board.turn  # Store as chess.WHITE or chess.BLACK
            turn_before_str = "White" if turn_before == chess.WHITE else "Black"
            
            # Verify it's a valid turn (game not over)
            if board.is_game_over():
                print(f"\nGame is over. Result: {board.result()}")
                return True
            
            # Let this agent make a move
            if agent.evolve(board, goal):
                # Goal achieved (checkmate)
                print(f"\nAgent {i+1} achieved checkmate!")
                return True
            
            # Check if a move was made
            moves_after = len(board.move_stack)
            turn_after = board.turn
            turn_after_str = "White" if turn_after == chess.WHITE else "Black"
            
            if goal.move_made and moves_after > moves_before:
                # Move was successfully made, board updated
                # CRITICAL: Verify turn alternated (White -> Black or Black -> White)
                if turn_after == turn_before:
                    print(f"\nERROR: Turn did not alternate! Still {turn_before_str}'s turn")
                    goal.move_made = False  # Mark as failed
                else:
                    # Move was successfully made, board updated, turn alternated
                    print(f"\nAgent {i+1} made move: {goal.move.uci() if goal.move else 'unknown'}")
                    print(f"  Board updated: {moves_before} -> {moves_after} moves")
                    print(f"  Turn changed: {turn_before_str} -> {turn_after_str} ✓")
                    # Continue to next agent (they'll see the updated board with opposite turn)
                    continue
            else:
                # No move was made by this agent (invalid move or error)
                print(f"\nAgent {i+1} failed to make a valid move")
                if goal.move:
                    attempted = goal.move.uci()
                    print(f"  Attempted move: {attempted}")
                    legal_moves_list = [m.uci() for m in list(board.legal_moves)]
                    if attempted in legal_moves_list:
                        print(f"  ERROR: Move is in legal moves but wasn't applied!")
                    else:
                        print(f"  Move not in legal moves list")
                        print(f"  Legal moves (first 15): {legal_moves_list[:15]}")
                elif goal.reason:
                    print(f"  No move was generated (reason available: {goal.reason[:50]}...)")
                # Try next agent (they might succeed)
                continue
        
        # All agents have had their turn
        # Return False if goal not achieved, True if achieved
        return goal.is_achieved()

