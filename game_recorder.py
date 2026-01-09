import json
import chess
import time
from datetime import datetime
from typing import List, Dict, Optional

class GameRecorder:
    """Records chess game moves with detailed intent, assumptions, threats, and evaluations."""
    
    def __init__(self):
        self.moves: List[Dict] = []
        self.initial_fen = chess.Board().fen()
        self.game_metadata = {
            "created_at": datetime.now().isoformat(),
            "agent_plays_first": None,
            "final_result": None,
            "total_moves": 0
        }
    
    def _uci_to_descriptive(self, move_uci: str, board: chess.Board) -> str:
        """Convert UCI move to descriptive format like 'Rd3-d5'."""
        try:
            move = chess.Move.from_uci(move_uci)
            from_square = chess.square_name(move.from_square)
            to_square = chess.square_name(move.to_square)
            
            # Get piece symbol
            piece = board.piece_at(move.from_square)
            if piece:
                piece_symbol = piece.symbol().upper()
                # Map piece symbols
                piece_map = {'P': '', 'N': 'N', 'B': 'B', 'R': 'R', 'Q': 'Q', 'K': 'K'}
                piece_str = piece_map.get(piece_symbol, '')
                
                # Format: Piece + from + - + to (e.g., "Rd3-d5")
                return f"{piece_str}{from_square}-{to_square}"
            else:
                return f"{from_square}-{to_square}"
        except:
            return move_uci
    
    def record_move(self, 
                   move_number: int,
                   actor: str,
                   move_uci: str,
                   board: chess.Board,
                   position_fen: Optional[str] = None,
                   intent_type: Optional[str] = None,
                   intent_description: Optional[str] = None,
                   assumptions: Optional[List[str]] = None,
                   threats_created: Optional[List[str]] = None,
                   risks_accepted: Optional[List[str]] = None,
                   expected_responses: Optional[List[str]] = None,
                   evaluation_self: Optional[str] = None,
                   evaluation_engine: Optional[str] = None,
                   plan_node: Optional[str] = None):
        """Record a move with detailed intent, assumptions, threats, and evaluations."""
        
        # Convert UCI to descriptive format
        move_descriptive = self._uci_to_descriptive(move_uci, board)
        
        move_data = {
            "move_number": move_number,
            "actor": actor,
            "move": move_descriptive,
            "position_fen": position_fen or board.fen(),
            "intent": {
                "type": intent_type or "unknown",
                "description": intent_description or ""
            },
            "assumptions": assumptions or [],
            "threats_created": threats_created or [],
            "risks_accepted": risks_accepted or [],
            "expected_responses": expected_responses or [],
            "evaluation_self": evaluation_self or None,
            "evaluation_engine": evaluation_engine or None,
            "plan_node": plan_node or None
        }
        self.moves.append(move_data)
        self.game_metadata["total_moves"] = len(self.moves)
    
    def set_metadata(self, agent_plays_first: bool, final_result: Optional[str] = None):
        """Set game metadata."""
        self.game_metadata["agent_plays_first"] = agent_plays_first
        if final_result:
            self.game_metadata["final_result"] = final_result
    
    def save_game(self, filename: Optional[str] = None, plan_dag = None) -> str:
        """Save the game to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"game_replay_{timestamp}.json"
        
        game_data = {
            "metadata": self.game_metadata,
            "initial_fen": self.initial_fen,
            "moves": self.moves
        }
        
        # Add PlanDAG structure if provided
        if plan_dag:
            game_data["plan_dag"] = plan_dag.to_dict()
        
        with open(filename, 'w') as f:
            json.dump(game_data, f, indent=2)
        
        return filename
    
    def load_game(self, filename: str) -> Dict:
        """Load a game from a JSON file."""
        with open(filename, 'r') as f:
            return json.load(f)
    
    def replay_game(self, filename: str, renderer=None, delay: float = 1.0):
        """Replay a saved game."""
        game_data = self.load_game(filename)
        
        board = chess.Board(game_data["initial_fen"])
        metadata = game_data["metadata"]
        moves = game_data["moves"]
        
        print(f"\n=== Replaying Game ===")
        print(f"Created: {metadata.get('created_at', 'Unknown')}")
        print(f"Agent plays first: {metadata.get('agent_plays_first', 'Unknown')}")
        print(f"Total moves: {len(moves)}")
        print(f"Final result: {metadata.get('final_result', 'Unknown')}")
        print("=" * 50)
        
        for move_data in moves:
            move_number = move_data["move_number"]
            actor = move_data.get("actor", move_data.get("player", "Unknown"))
            move_str = move_data.get("move", move_data.get("move_uci", ""))
            position_fen = move_data.get("position_fen", "")
            intent = move_data.get("intent", {})
            
            # Try to get move_uci from the move string or use descriptive format
            move_uci = None
            if "-" in move_str:
                # Descriptive format like "Rd3-d5", convert back to UCI
                try:
                    parts = move_str.split("-")
                    if len(parts) == 2:
                        from_sq = parts[0][-2:] if len(parts[0]) > 2 else parts[0]
                        to_sq = parts[1]
                        move_uci = f"{from_sq}{to_sq}"
                except:
                    pass
            
            if not move_uci:
                move_uci = move_data.get("move_uci", move_str)
            
            print(f"\nMove {move_number}: {actor} plays {move_str}")
            if intent.get("description"):
                print(f"  Intent: {intent.get('type', 'unknown')} - {intent.get('description', '')}")
            
            # Apply the move
            try:
                move = chess.Move.from_uci(move_uci)
                board.push(move)
                
                # Build reason string from intent
                reason_str = intent.get("description", "")
                if not reason_str:
                    reason_str = f"{intent.get('type', 'unknown')} move"
                
                # Render if renderer is provided
                if renderer:
                    renderer.render(
                        board, 
                        reason=reason_str, 
                        move=move_str, 
                        goal=None
                    )
                    time.sleep(delay)
            except Exception as e:
                print(f"  ERROR applying move: {e}")
                break
            
            if board.is_game_over():
                print(f"\nGame Over: {board.result()}")
                break
        
        print("\n=== Replay Complete ===")
        return board
