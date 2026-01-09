"""
Plan Directed Acyclic Graph (DAG) for chess game planning.
Represents hierarchical strategic plans and their execution.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

class PlanType(Enum):
    """Types of strategic plans"""
    CONTROL_CENTER = "Control Center"
    DEVELOP_KINGSIDE = "Develop Kingside"
    DEVELOP_QUEENSIDE = "Develop Queenside"
    CENTRAL_BREAK = "Central Break"
    KINGSIDE_PRESSURE = "Kingside Pressure"
    QUEENSIDE_PRESSURE = "Queenside Pressure"
    DEFENSIVE_SOLIDIFICATION = "Defensive Solidification"
    TACTICAL_EXPLOITATION = "Tactical Exploitation"
    MATERIAL_GAIN = "Material Gain"
    POSITIONAL_IMPROVEMENT = "Positional Improvement"
    COUNTER_ATTACK = "Counter Attack"
    ENDGAME_TRANSITION = "Endgame Transition"

@dataclass
class PlanNode:
    """A node in the plan DAG representing a strategic plan or sub-plan"""
    plan_id: str
    plan_type: PlanType
    description: str
    parent_id: Optional[str] = None  # Parent plan node
    children_ids: List[str] = field(default_factory=list)  # Child plan nodes
    moves: List[str] = field(default_factory=list)  # Moves that execute this plan
    status: str = "active"  # active, completed, abandoned
    created_at_move: int = 0
    
    def get_path(self, dag: 'PlanDAG') -> str:
        """Get the full path from root to this node"""
        path_parts = [self.plan_type.value]
        current = self
        while current.parent_id:
            parent = dag.get_node(current.parent_id)
            if parent:
                path_parts.insert(0, parent.plan_type.value)
                current = parent
            else:
                break
        return " → ".join(path_parts)
    
    def get_execution_path(self, move: str) -> str:
        """Get the execution path for a specific move"""
        base_path = self.get_path(None) if not hasattr(self, '_dag') else self.get_path(self._dag)
        return f"{base_path} → {move} execution"

class PlanDAG:
    """Directed Acyclic Graph of strategic plans"""
    
    def __init__(self):
        self.nodes: Dict[str, PlanNode] = {}
        self.root_nodes: List[str] = []  # Top-level plans
        self.move_to_plan: Dict[str, str] = {}  # Map move UCI to plan_id
        self._next_id = 1
    
    def _generate_id(self) -> str:
        """Generate a unique plan ID"""
        plan_id = f"plan_{self._next_id}"
        self._next_id += 1
        return plan_id
    
    def create_plan(self, 
                   plan_type: PlanType,
                   description: str,
                   parent_id: Optional[str] = None,
                   move_number: int = 0) -> str:
        """Create a new plan node"""
        plan_id = self._generate_id()
        node = PlanNode(
            plan_id=plan_id,
            plan_type=plan_type,
            description=description,
            parent_id=parent_id,
            created_at_move=move_number
        )
        node._dag = self  # Reference for path calculation
        self.nodes[plan_id] = node
        
        # Add to parent's children
        if parent_id:
            parent = self.nodes.get(parent_id)
            if parent:
                parent.children_ids.append(plan_id)
        else:
            self.root_nodes.append(plan_id)
        
        return plan_id
    
    def get_node(self, plan_id: str) -> Optional[PlanNode]:
        """Get a plan node by ID"""
        return self.nodes.get(plan_id)
    
    def add_move_to_plan(self, move_uci: str, plan_id: str):
        """Associate a move with a plan"""
        node = self.nodes.get(plan_id)
        if node:
            if move_uci not in node.moves:
                node.moves.append(move_uci)
            self.move_to_plan[move_uci] = plan_id
    
    def get_plan_for_move(self, move_uci: str) -> Optional[PlanNode]:
        """Get the plan node for a specific move"""
        plan_id = self.move_to_plan.get(move_uci)
        if plan_id:
            return self.nodes.get(plan_id)
        return None
    
    def get_plan_path_for_move(self, move_uci: str) -> Optional[str]:
        """Get the full plan path string for a move (e.g., 'Central Break → d5 execution')"""
        node = self.get_plan_for_move(move_uci)
        if node:
            # Get the move description (e.g., "d5" from "d2d5")
            move_desc = move_uci[-2:] if len(move_uci) >= 4 else move_uci
            base_path = node.get_path(self)
            return f"{base_path} → {move_desc} execution"
        return None
    
    def get_active_plans(self) -> List[PlanNode]:
        """Get all currently active plans"""
        return [node for node in self.nodes.values() if node.status == "active"]
    
    def complete_plan(self, plan_id: str):
        """Mark a plan as completed"""
        node = self.nodes.get(plan_id)
        if node:
            node.status = "completed"
    
    def abandon_plan(self, plan_id: str):
        """Mark a plan as abandoned"""
        node = self.nodes.get(plan_id)
        if node:
            node.status = "abandoned"
    
    def to_dict(self) -> Dict:
        """Convert the DAG to a dictionary for serialization"""
        return {
            "nodes": {
                plan_id: {
                    "plan_id": node.plan_id,
                    "plan_type": node.plan_type.value,
                    "description": node.description,
                    "parent_id": node.parent_id,
                    "children_ids": node.children_ids,
                    "moves": node.moves,
                    "status": node.status,
                    "created_at_move": node.created_at_move
                }
                for plan_id, node in self.nodes.items()
            },
            "root_nodes": self.root_nodes,
            "move_to_plan": self.move_to_plan
        }
    
    def from_dict(self, data: Dict):
        """Load the DAG from a dictionary"""
        self.nodes = {}
        self.root_nodes = data.get("root_nodes", [])
        self.move_to_plan = data.get("move_to_plan", {})
        
        for plan_id, node_data in data.get("nodes", {}).items():
            node = PlanNode(
                plan_id=node_data["plan_id"],
                plan_type=PlanType(node_data["plan_type"]),
                description=node_data["description"],
                parent_id=node_data.get("parent_id"),
                children_ids=node_data.get("children_ids", []),
                moves=node_data.get("moves", []),
                status=node_data.get("status", "active"),
                created_at_move=node_data.get("created_at_move", 0)
            )
            node._dag = self
            self.nodes[plan_id] = node
