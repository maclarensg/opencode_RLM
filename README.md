<# OpenCode RLM - SRE/DevOps Edition

Inspired by brainqub3 claude_code_RLM, this is an OpenCode version for RLM (Recursive Language Model)

A Recursive Language Model (RLM) implementation for OpenCode, specialized for Site Reliability Engineering and DevOps workflows.

## About

This repository provides an RLM setup that enables OpenCode to process documents and contexts that exceed typical context window limits. It implements the core RLM pattern where a root language model orchestrates sub-LLM calls over chunks of a large document.

**Use cases:**
- Analyzing large log files (application logs, system logs, audit logs)
- Processing Kubernetes manifests and cluster state dumps
- Reviewing Terraform state and plan outputs
- Investigating incident timelines
- Parsing configuration files and infrastructure code

## Architecture

This implementation maps to the RLM paper architecture:

| RLM Concept | Implementation | Model |
|-------------|----------------|-------|
| Root LLM | Main OpenCode conversation | **Claude Sonnet 4** |
| Sub-LLM (`llm_query`) | `rlm-subcall` subagent | **Claude Haiku 4** |
| External Environment | Persistent Python REPL (`rlm_repl.py`) | Python 3 |

```
┌─────────────────────────────────────────────────────────┐
│                    Root LLM (Sonnet)                     │
│                   Main Conversation                      │
│                  SRE/DevOps Expert                       │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│  Python REPL    │         │  rlm-subcall    │
│  (Environment)  │         │  (Haiku Sub-LM) │
│                 │         │                 │
│ - Load context  │         │ - Analyze chunk │
│ - Chunk data    │         │ - Extract info  │
│ - Search/grep   │         │ - Return JSON   │
│ - Store results │         │                 │
└─────────────────┘         └─────────────────┘
```

## Prerequisites

- **OpenCode** - [Install OpenCode](https://opencode.ai/docs/)
- **Python 3** - For the persistent REPL environment
- **API Keys** - Anthropic API key configured in OpenCode

## Quick Start

1. **Navigate to this directory**
   ```bash
   cd opencode_RLM
   ```

2. **Start OpenCode**
   ```bash
   opencode
   ```

3. **Use the RLM workflow**
   ```
   /rlm context=/path/to/large-logfile.log query="Find all errors and their root causes"
   ```

## Available Agents

### Primary Agents (Tab to switch)

| Agent | Description | Use Case |
|-------|-------------|----------|
| `sre-build` | Full operational access | Making changes, implementing fixes |
| `sre-plan` | Read-only analysis mode | Safe investigation, planning |

### Subagents (@mention to invoke)

| Agent | Description | Use Case |
|-------|-------------|----------|
| `rlm-subcall` | Chunk analyzer | RLM workflow chunk processing |
| `log-analyzer` | Log specialist | Log file analysis |
| `k8s-expert` | Kubernetes specialist | K8s troubleshooting |
| `terraform-expert` | IaC specialist | Terraform review |

## Custom Commands

| Command | Description |
|---------|-------------|
| `/rlm` | Run RLM workflow for large context processing |
| `/incident` | Start incident investigation workflow |
| `/k8s-debug` | Debug Kubernetes issues |
| `/tf-plan` | Review Terraform changes |
| `/analyze-logs` | Analyze log files |
| `/runbook` | Generate operational runbook |
| `/postmortem` | Create incident postmortem |
| `/slo-review` | Review SLO compliance |

## RLM REPL Commands

The REPL provides these helper functions:

```python
# Basic operations
peek(start, end)              # View slice of content
grep(pattern, max_matches)    # Search with regex
grep_count(pattern)           # Count pattern occurrences
find_lines(pattern)           # Find matching lines with numbers

# Chunking
chunk_indices(size, overlap)  # Get chunk boundaries
write_chunks(out_dir, size)   # Write chunks to files

# Analysis helpers
stats()                       # Get content statistics
time_range()                  # Extract time range from logs
extract_json_objects()        # Parse JSONL content
extract_yaml_documents()      # Split YAML documents

# State management
add_buffer(text)              # Store intermediate results
```

## Repository Structure

```
opencode_RLM/
├── AGENTS.md                      # Main agent instructions (SRE/DevOps focus)
├── opencode.json                  # OpenCode configuration
├── README.md                      # This file
├── .opencode/
│   ├── agents/
│   │   └── rlm-subcall.md        # Sub-LLM agent definition
│   ├── skills/
│   │   └── rlm/
│   │       ├── SKILL.md          # RLM skill definition
│   │       └── scripts/
│   │           └── rlm_repl.py   # Persistent Python REPL
│   └── commands/                  # Custom slash commands
├── prompts/
│   ├── sre-build.md              # Build agent prompt
│   ├── sre-plan.md               # Plan agent prompt
│   ├── log-analyzer.md           # Log analyzer prompt
│   ├── k8s-expert.md             # Kubernetes expert prompt
│   └── terraform-expert.md       # Terraform expert prompt
├── knowledge/
│   ├── incident-response.md      # Incident response knowledge
│   └── sre-best-practices.md     # SRE best practices
└── context/                       # Place large files here
```

## Example Workflows

### Analyzing Application Logs

```
# Start OpenCode
opencode

# Use RLM for large log files
/rlm context=./context/app.log query="Find all errors in the last hour and identify the root cause"
```

### Kubernetes Troubleshooting

```
# Dump cluster state
kubectl get all -A -o yaml > context/cluster-state.yaml

# Analyze with RLM
/rlm context=./context/cluster-state.yaml query="Find pods with restart loops and resource issues"
```

### Terraform Review

```
# Generate plan
terraform plan -out=tfplan
terraform show -json tfplan > context/tfplan.json

# Review with RLM
/rlm context=./context/tfplan.json query="Identify high-risk changes and security concerns"
```

## Security Notes

- The REPL executes arbitrary Python code - treat it like running your own scripts
- Sensitive data in context files stays local (not sent to cloud unless in chunks)
- Review permissions before running in production environments
- Use `sre-plan` agent for safe, read-only investigation

## Based On

> **Recursive Language Models**
> Alex L. Zhang, Tim Kraska, Omar Khattab
> MIT CSAIL
> [arXiv:2512.24601](https://arxiv.org/abs/2512.24601)

Adapted from [claude_code_RLM](https://github.com/Brainqub3/claude_code_RLM) for OpenCode with SRE/DevOps specialization.

## License

MIT License - See LICENSE for details.

