# SPARC: Self-Replicating Agents with Resource Caps

A population of LLM agents that can spawn modified copies of themselves, compete for limited resources, and go extinct, producing evolutionary intelligence rather than task orchestration.

## Overview

SPARC implements an evolutionary system where agents:
- **Replicate**: Agents can spawn mutated copies of themselves
- **Compete**: Agents compete for limited resources (API calls, compute time, memory)
- **Evolve**: Mutations occur in prompts, parameters, and behavior strategies
- **Survive**: Fitness is based on longevity - agents that survive longer thrive
- **Go Extinct**: Resource exhaustion and poor performance lead to natural selection

## Architecture

The system consists of several key components:

- **Agent Core**: Individual agents with replication, mutation, and resource tracking
- **Resource Manager**: Global resource pools with caps and first-come-first-served allocation
- **Evolution Engine**: Main simulation loop managing population dynamics
- **Mutation System**: Strategies for modifying agent copies (prompts, parameters, behavior)
- **Survival System**: Resource competition and extinction mechanisms
- **LLM Integration**: Local model interface (Ollama-compatible)

### System Flow

```
Initialize Population → Evolution Loop → Resource Allocation → Agent Actions
                                                                    ↓
                                    ← Replication & Mutation ← Survival Challenges
                                                                    ↓
                                                              Extinction Check
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Ollama installed and running (or compatible local LLM service)

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure Ollama is running:
```bash
# Install Ollama from https://ollama.ai
ollama serve
# Pull a model (e.g., llama2)
ollama pull llama2
```

## Configuration

Edit `config/default.yaml` to customize the simulation:

```yaml
population:
  initial_size: 10      # Starting number of agents
  max_size: 100         # Maximum population size

resources:
  api_calls_per_minute: 100    # API call limit per minute
  compute_time_per_minute: 60  # CPU seconds per minute
  memory_mb: 1024              # Memory limit in MB

mutation:
  replication_rate: 0.1         # Base probability of replication per cycle
  prompt_mutation_rate: 0.3     # Rate of prompt mutations
  parameter_mutation_rate: 0.2   # Rate of parameter mutations
  behavior_mutation_rate: 0.1    # Rate of behavior mutations

llm:
  base_url: "http://localhost:11434"  # Ollama API URL
  default_model: "llama2"             # Default model name

evolution:
  cycles_per_generation: 100          # Cycles per generation
  extinction_threshold: 0.1            # Resource threshold for extinction (10%)
```

## Usage

### Basic Usage

Run the simulation with default configuration:

```bash
python main.py
```

### Command Line Options

```bash
python main.py --help
```

Options:
- `-c, --config PATH`: Path to configuration file (default: `config/default.yaml`)
- `-g, --generations N`: Maximum number of generations to run
- `-l, --log-level LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--log-dir DIR`: Directory for log files (default: `logs`)

### Examples

Run for 5 generations:
```bash
python main.py -g 5
```

Run with custom config and debug logging:
```bash
python main.py -c config/custom.yaml -l DEBUG
```

## How It Works

### Agent Lifecycle

1. **Initialization**: Random agents are created with varied prompts, parameters, and behaviors
2. **Action Phase**: Each cycle, agents attempt to:
   - Request resources (API calls, compute, memory)
   - Face survival challenges
   - Resource allocation challenges
   - Competition scenarios
   - Efficiency tests
3. **Replication**: Agents may spawn mutated offspring if:
   - Resources are available
   - Population is below maximum
   - Replication probability is met
4. **Mutation**: Offspring inherit parent traits with mutations:
   - **Prompt mutations**: Text variations, additions, deletions
   - **Parameter mutations**: Temperature, top_p adjustments
   - **Behavior mutations**: Strategy changes (conservative/aggressive/balanced)
5. **Extinction**: Agents go extinct when:
   - Resources are critically low
   - Agent efficiency is very poor
   - Maximum age is reached
6. **Selection**: Agents with higher longevity and resource efficiency survive longer

### Resource Competition

Resources are allocated on a **first-come-first-served** basis, creating natural competition:
- Agents that request resources early get them
- Agents that use resources efficiently survive longer
- Resource exhaustion creates selection pressure

### Fitness Evaluation

Fitness is primarily based on **longevity** (age in cycles):
- Agents that survive more cycles have higher fitness
- Resource efficiency is a secondary factor
- Replication success contributes to fitness

## Output

The system generates:

1. **Console Output**: Real-time progress and statistics
2. **Log Files**: Detailed logs in `logs/sparc_YYYYMMDD_HHMMSS.log`
3. **Statistics Files**: JSON statistics in `logs/statistics_YYYYMMDD_HHMMSS.json`

### Statistics Include

- Population size over time
- Replication and extinction counts
- Average age and longevity
- Resource usage patterns
- Generation-by-generation breakdown

## Example Output

```
SPARC: Self-Replicating Agents with Resource Caps
Logging to: logs/sparc_20250107_212000.log

Configuration loaded from: config/default.yaml
Starting evolution simulation...

INFO - Starting evolution simulation
INFO - Initializing population of 10 agents
INFO - Starting generation 1
INFO - Cycle 1 complete: population=10, active=10, replications=1, extinct=0
...
INFO - Generation 1 complete: population 10 -> 12, replications=3, extinctions=0

============================================================
EVOLUTION STATISTICS SUMMARY
============================================================
Total Generations: 5
Initial Population: 10
Final Population: 15
Population Change: +5
Total Replications: 12
Total Extinctions: 2
Avg Replications/Generation: 2.40
Avg Extinctions/Generation: 0.40

Final Survival Statistics:
  Active Agents: 13
  Average Age: 8.5
  Average Longevity: 8.5
  Average Efficiency: 2.3
  Total Offspring: 12
  Max Generation: 3
============================================================
```

## Customization

### Adding Custom Mutations

Edit `src/mutations.py` to add new mutation strategies.

### Custom Survival Challenges

Modify `src/survival.py` to add new challenge types.

### Different LLM Providers

Update `src/llm_client.py` to support other LLM APIs (OpenAI, Anthropic, etc.).

## Troubleshooting

### Ollama Not Available

If Ollama is not running, the system will continue with limited functionality. Agents will still compete for resources and evolve, but LLM-based decision making will be disabled.

### Resource Exhaustion

If resources are exhausted too quickly:
- Increase resource caps in configuration
- Reduce population size
- Adjust mutation/replication rates

### Performance Issues

For large populations:
- Reduce `cycles_per_generation`
- Increase resource caps
- Use faster/smaller LLM models

## License

This project is provided as-is for research and experimentation purposes.

## Contributing

This is an experimental system. Feel free to modify and extend it for your own research!

## Acknowledgments

SPARC is inspired by evolutionary algorithms and artificial life systems, applying these concepts to LLM agents in a resource-constrained environment.
