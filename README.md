# chessXAI: LLM-Powered Chess Agent with Strategic Planning

A chess AI system that uses Large Language Models (LLMs) to play chess against Stockfish, with advanced strategic planning, move reasoning, and game analysis capabilities.

## Overview

chessXAI combines:
- **LLM Agents**: Uses OpenAI, Anthropic, or Ollama models to generate chess moves with strategic reasoning
- **Strategic Planning**: Tracks game plans as a Directed Acyclic Graph (DAG) with hierarchical plan structures
- **Game Recording**: Comprehensive move logging with intent, assumptions, threats, and evaluations
- **Visualization**: Real-time Pygame-based board rendering with move details
- **Analysis Tools**: Plan DAG visualization and game replay capabilities

## Features

### Core Capabilities

- **LLM-Powered Move Generation**: Agents use LLMs to generate moves with strategic reasoning
- **Plan-Based Strategy**: Tracks strategic plans (Control Center, Development, Defensive, etc.) as a DAG
- **Move Validation**: Ensures only legal moves are selected from provided move lists
- **Detailed Game Recording**: Records moves with intent, assumptions, threats, risks, and evaluations
- **Real-Time Visualization**: Pygame-based board rendering with piece display and move information
- **Game Replay**: Replay saved games with full move history and reasoning

### Strategic Planning

The system tracks strategic plans as a Directed Acyclic Graph:
- **Plan Types**: Control Center, Development, Defensive, Tactical, etc.
- **Hierarchical Structure**: Plans can have parent-child relationships
- **Plan Lifecycle**: Plans transition through states (active, completed, abandoned, failed, forced)
- **Move Association**: Each move is linked to a strategic plan

## Installation

### Prerequisites

- Python 3.8 or higher
- Stockfish chess engine (download from https://stockfishchess.org/download/)
- LLM API access (OpenAI, Anthropic, or local Ollama)

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install langchain-ollama langchain-openai langchain-anthropic python-chess pygame python-dotenv pydantic
```

3. Install Stockfish:
   - **Windows**: Download from https://stockfishchess.org/download/ and extract to `engine/stockfish/`
   - **Linux**: `sudo apt-get install stockfish` or download binary
   - **Mac**: `brew install stockfish` or download binary

4. Configure API keys (create `.env` file):
```env
OPENAI_API_KEY=your_openai_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_key_here
```

5. Update `main.py` to set the Stockfish path:
```python
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "engine", "stockfish", "stockfish.exe")
# Adjust path for your system
```

## Configuration

Edit `config.py` and `main.py` to customize:

### LLM Configuration (`config.py`)
```python
# Choose LLM provider
llm_type = LLMType.OPENAI  # OPENAI, ANTHROPIC, or OLLAMA
llm_model = "gpt-4"  # Model name
temperature = 0.2  # Lower = more deterministic
```

### Game Configuration (`main.py`)
```python
# Choose who plays first
AGENT_PLAYS_FIRST = True  # True = Agent plays White, False = Stockfish plays White

# Stockfish thinking time
stockfish.play(board, chess.engine.Limit(time=1.0))  # Adjust time limit
```

## Usage

### Basic Game Play

Run a game between the LLM agent and Stockfish:

```bash
python main.py
```

The game will:
1. Initialize the board and players
2. Alternate moves between agent and Stockfish
3. Display the board in real-time with Pygame
4. Record all moves with detailed information
5. Save the game to a JSON file when complete

### Game Recording

Games are automatically saved to `game_replay_YYYYMMDD_HHMMSS.json` with:
- Complete move history
- Intent descriptions for each move
- Strategic plan associations
- Plan DAG structure
- Assumptions, threats, risks, and evaluations

### Replay a Game

Replay a saved game:

```bash
python replay_game.py game_replay_20260109_142600.json
```

### Visualize Plan DAG

Visualize the strategic plan structure:

```bash
python eval.py game_replay_20260109_142600.json
```

This generates a visual graph of the plan DAG showing:
- Plan hierarchy and relationships
- Move associations
- Plan status (active, completed, failed, etc.)
- Textual analysis of the game strategy

## Architecture

### Core Components

- **`models.py`**: LLM agent implementation with move generation and validation
- **`game_recorder.py`**: Game recording with detailed move metadata
- **`plan_dag.py`**: Strategic plan DAG data structures and management
- **`render.py`**: Pygame-based board visualization
- **`main.py`**: Main game loop orchestrating agent vs Stockfish
- **`replay_game.py`**: Game replay functionality
- **`eval.py`**: Plan DAG visualization and analysis

### System Flow

```
Initialize Board & Players
    ↓
Game Loop:
  Agent Turn → LLM generates move → Validate → Apply → Record
    ↓
  Stockfish Turn → Engine calculates → Apply → Record
    ↓
  Render Board → Check Game Status
    ↓
Save Game → Generate Plan DAG → Visualize
```

## Move Generation

The LLM agent:
1. Receives current board state (FEN notation)
2. Gets list of legal moves (UCI notation)
3. Considers active strategic plans
4. Generates move with reasoning and plan association
5. Move is validated against legal moves list
6. Only valid moves are accepted (with fallback if needed)

### Strategic Planning

The agent thinks in terms of strategic plans:
- **Control Center**: Central pawn advances (e4, d4)
- **Development**: Piece development (Nf3, Bc4, castling)
- **Defensive**: Responding to threats, protecting pieces
- **Tactical**: Exploiting tactical opportunities
- **Material Gain**: Capturing pieces, winning material

Plans are tracked as a DAG where:
- Root plans represent major strategic themes
- Sub-plans represent specific execution steps
- Moves are associated with plans
- Plans transition based on game events

## Game Record Format

Each move is recorded with:

```json
{
  "move_number": 1,
  "actor": "GPT-5.1",
  "move": "e2-e4",
  "move_uci": "e2e4",
  "position_fen": "...",
  "intent": {
    "type": "Control Center",
    "description": "Establish central control with e4"
  },
  "assumptions": [...],
  "threats_created": [...],
  "risks_accepted": [...],
  "expected_responses": [...],
  "evaluation_self": "...",
  "evaluation_engine": null,
  "plan_node": "Control Center → e4 execution"
}
```

## Plan DAG Structure

The Plan DAG tracks strategic thinking:

```json
{
  "nodes": {
    "plan_1": {
      "plan_type": "Control Center",
      "description": "Establish central pawn presence",
      "moves": ["e2e4", "d2d4"],
      "status": "active",
      "created_at_move": 1
    }
  },
  "root_nodes": ["plan_1"],
  "move_to_plan": {
    "e2e4": "plan_1",
    "d2d4": "plan_1"
  }
}
```

## Customization

### Adding New Plan Types

Edit `plan_dag.py`:

```python
class PlanType(Enum):
    # ... existing types ...
    YOUR_NEW_PLAN = "Your New Plan"
```

### Custom LLM Prompts

Modify `GoalPrompt` in `models.py` to change how the agent thinks about moves.

### Visualization Customization

Edit `render.py` to customize board appearance, colors, or information display.

## Troubleshooting

### Stockfish Not Found

Ensure Stockfish is installed and the path in `main.py` is correct:
```python
ENGINE_PATH = "path/to/stockfish/executable"
```

### LLM API Errors

- Check API keys in `.env` file
- Verify API quota/limits
- Check network connectivity

### Pygame Display Issues

- Ensure display is available (for headless servers, use Xvfb or similar)
- Check font availability for chess piece symbols

### Move Validation Errors

The system automatically validates moves and uses fallbacks if the LLM generates invalid moves. Check console output for validation messages.

## Example Output

```
=== Stockfish vs Agent Game ===
Agent plays as White, Stockfish plays as Black
Starting game...

--- Move 1: White's turn ---
Agent is thinking (White)...
  VALIDATED: Move 'e2e4' is in allowed moves list ✓
  Plan: Control Center → e4 execution
Agent (White) played: e2e4
Reason: Establish central control with e4

--- Move 2: Black's turn ---
Stockfish is thinking (Black)...
Stockfish (Black) played: e7e5

...

Game saved to: game_replay_20260109_142600.json
Plan DAG structure saved with 5 plan nodes
```

## License

This project is provided as-is for research and experimentation purposes.

## Acknowledgments

chessXAI demonstrates how LLMs can be applied to strategic games, combining:
- Natural language reasoning for move selection
- Structured planning for long-term strategy
- Integration with traditional chess engines
- Comprehensive game analysis and visualization
