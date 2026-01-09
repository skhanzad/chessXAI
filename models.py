from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from config import LLMConfig, LLMType

import chess

from pydantic import BaseModel, Field

GoalPrompt = PromptTemplate(
    input_variables=["board", "goal", "format_instructions", "turn", "legal_moves", "active_plans"],
    template="""
    You are a chess agent that thinks in terms of strategic plans.
    You are given a goal to solve and need to make a move that fits into a strategic plan.
    
    Goal: {goal}
    
    The chess board is given below (FEN notation):
    {board}
    
    CRITICAL: It is currently {turn}'s turn to move.
    
    IMPORTANT: The board state has changed since the last move. Previous moves are no longer available.
    You MUST look at the CURRENT board state and legal moves list below.
    
    ================================================================================
    ACTIVE STRATEGIC PLANS:
    ================================================================================
    {active_plans}
    
    You should either:
    1. Continue executing an existing active plan
    2. Create a new strategic plan if the position requires it
    3. Create a sub-plan under an existing plan
    
    Common plan types include:
    - Control Center (controlling central squares)
    - Develop Kingside / Develop Queenside (piece development)
    - Central Break (breaking in the center with pawns)
    - Kingside Pressure / Queenside Pressure (attacking on a flank)
    - Defensive Solidification (strengthening the position)
    - Tactical Exploitation (taking advantage of tactics)
    - Material Gain (winning material)
    - Positional Improvement (improving piece placement)
    
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
    
    STRATEGIC PLANNING:
    - Identify which strategic plan your move belongs to
    - If continuing an existing plan, use that plan_type and parent_plan
    - If starting a new plan, specify the plan_type and leave parent_plan empty
    - If creating a sub-plan, specify both plan_type and parent_plan
    
    Examples of UCI notation format:
    - "e2e4" means pawn moves from e2 to e4
    - "g1f3" means knight moves from g1 to f3
    - "e1g1" means king castles kingside (e1 to g1)
    
    Provide the move, explain your reasoning, and specify the strategic plan information.
    
    {format_instructions}
    """
)

class Output(BaseModel):
    move: str = Field(description="The move to make in UCI notation. MUST be exactly one of the legal moves provided in the prompt. Copy it exactly as it appears in the legal moves list (e.g., 'e2e4', 'g1f3').")
    reason: str = Field(description="The reason for the move")
    new_goal: str = Field(description="The new goal to solve")
    plan_type: str = Field(description="The strategic plan type this move belongs to (e.g., 'Control Center', 'Develop Kingside', 'Central Break', 'Kingside Pressure', etc.)")
    plan_description: str = Field(description="A brief description of the strategic plan or sub-plan this move executes")
    parent_plan: str = Field(description="The parent plan this move belongs to, if any (e.g., 'Control Center' for a 'Develop Kingside' sub-plan). Leave empty if this is a top-level plan.")


class Goal:
    def __init__(self, description: str):
        self.original_description = description
        self.description = description
        self.achieved = False
        self.move = None
        self.reason = None
        self.move_made = False  # Track if a valid move was made
        self.plan_node = None  # Plan node path for this move

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
                
                # Note: Turn naturally alternates in chess after a valid move
                if board.is_checkmate():
                    self.achieved = True
                else:
                    self.achieved = False
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
                model=config.llm_model,
                temperature=config.temperature,
                base_url=config.base_url,
                api_key=config.api_key
            )
        elif config.llm_type == LLMType.OPENAI:
            self.llm = ChatOpenAI(
                model=config.llm_model,
                temperature=config.temperature,
                api_key=config.api_key
            )
        elif config.llm_type == LLMType.ANTHROPIC:
            self.llm = ChatAnthropic(
                model=config.llm_model,
                temperature=config.temperature,
                api_key=config.api_key
            )

    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    def evolve(self, board: chess.Board = None, goal: Goal = None, plan_dag = None, move_number: int = 0):
        """
        Evolve the agent based on the goal to solve.
        Ensures only valid moves are chosen and moves are made in the correct turn.
        """
        parser = PydanticOutputParser(pydantic_object=Output)
        chain = GoalPrompt | self.llm | parser
        
        # Determine whose turn it is - CRITICAL: only make moves for the current player
        turn = "White" if board.turn == chess.WHITE else "Black"
        expected_color = board.turn  # Store expected color to verify later
        
        # Get active plans information
        active_plans_str = "No active plans"
        if plan_dag:
            active_plans = plan_dag.get_active_plans()
            if active_plans:
                plan_lines = []
                for plan in active_plans:
                    plan_path = plan.get_path(plan_dag)
                    plan_lines.append(f"- {plan_path}: {plan.description} (moves: {', '.join(plan.moves[-3:]) if plan.moves else 'none'})")
                active_plans_str = "\n".join(plan_lines)
        
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
                "active_plans": active_plans_str,
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
        
        # Process plan information and update PlanDAG
        plan_node_path = None
        if plan_dag and hasattr(result, 'plan_type') and result.plan_type:
            try:
                from plan_dag import PlanType
                
                # Try to find matching plan type
                plan_type = None
                for pt in PlanType:
                    if pt.value.lower() == result.plan_type.lower():
                        plan_type = pt
                        break
                
                if not plan_type:
                    # Create a custom plan type (will need to handle this)
                    plan_type = PlanType.POSITIONAL_IMPROVEMENT  # Default fallback
                
                # Find parent plan if specified
                parent_plan_id = None
                if hasattr(result, 'parent_plan') and result.parent_plan:
                    # Find parent plan by type
                    active_plans = plan_dag.get_active_plans()
                    for plan in active_plans:
                        if plan.plan_type.value.lower() == result.parent_plan.lower():
                            parent_plan_id = plan.plan_id
                            break
                
                # Create or find the plan
                plan_id = None
                if parent_plan_id:
                    # Check if sub-plan already exists
                    parent_plan = plan_dag.get_node(parent_plan_id)
                    if parent_plan:
                        for child_id in parent_plan.children_ids:
                            child = plan_dag.get_node(child_id)
                            if child and child.plan_type == plan_type and child.status == "active":
                                plan_id = child_id
                                break
                
                if not plan_id:
                    # Create new plan
                    plan_id = plan_dag.create_plan(
                        plan_type=plan_type,
                        description=result.plan_description if hasattr(result, 'plan_description') else result.plan_type,
                        parent_id=parent_plan_id,
                        move_number=move_number
                    )
                
                # Associate move with plan
                plan_dag.add_move_to_plan(move_to_apply, plan_id)
                
                # Get the plan path for this move
                plan_node_path = plan_dag.get_plan_path_for_move(move_to_apply)
                print(f"  Plan: {plan_node_path}")
                
            except Exception as e:
                print(f"  Warning: Error processing plan information: {e}")
                import traceback
                traceback.print_exc()
        
        # Store plan_node in goal for recording
        if plan_node_path:
            goal.plan_node = plan_node_path
        
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



