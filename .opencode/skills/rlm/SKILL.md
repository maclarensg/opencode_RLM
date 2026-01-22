---
name: rlm
description: Run a Recursive Language Model-style loop for long-context tasks (logs, configs, manifests). Uses a persistent Python REPL and rlm-subcall subagent for chunk-level analysis.
---

# rlm (Recursive Language Model workflow)

Use this Skill when:
- The user provides (or references) a very large context file (logs, configs, Kubernetes manifests, Terraform state, etc.) that won't fit comfortably in chat context.
- You need to iteratively inspect, search, chunk, and extract information from that context.
- You need to delegate chunk-level analysis to a subagent for efficient processing.

## Mental Model

- Main OpenCode conversation = the root LM (orchestrator)
- Persistent Python REPL (`rlm_repl.py`) = the external environment for state management
- Subagent `rlm-subcall` = the sub-LM used for chunk analysis (like `llm_query` in RLM paper)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Root LLM (Sonnet)                     │
│                   Main Conversation                      │
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
│ - Store results │         │ - Return JSON   │
└─────────────────┘         └─────────────────┘
```

## How to Run

### Inputs

This Skill accepts these patterns:
- `context=<path>` (required): path to the file containing the large context
- `query=<question>` (required): what the user wants to know
- Optional: `chunk_chars=<int>` (default ~200000) and `overlap_chars=<int>` (default 0)

If arguments weren't supplied, ask for:
1. The context file path
2. The query/question

### Step-by-step Procedure

1. **Initialize the REPL state**
   ```bash
   python3 .opencode/skills/rlm/scripts/rlm_repl.py init <context_path>
   python3 .opencode/skills/rlm/scripts/rlm_repl.py status
   ```

2. **Scout the context quickly**
   ```bash
   # Preview beginning
   python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(peek(0, 3000))"
   
   # Preview end
   python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(peek(len(content)-3000, len(content)))"
   ```

3. **Choose a chunking strategy**
   - For logs: chunk by time windows or size
   - For Kubernetes manifests: chunk by resource
   - For Terraform: chunk by module/resource type
   - For JSON/YAML configs: chunk by top-level keys
   - Default: chunk by characters (size around chunk_chars)

4. **Materialize chunks as files** (so subagents can read them)
   ```bash
   python3 .opencode/skills/rlm/scripts/rlm_repl.py exec <<'PY'
   paths = write_chunks('.opencode/rlm_state/chunks', size=200000, overlap=0)
   print(f"Created {len(paths)} chunks")
   print(paths[:5])
   PY
   ```

5. **Subcall loop** (delegate to rlm-subcall)
   - For each chunk file, invoke the `@rlm-subcall` subagent with:
     - The user query
     - The chunk file path
     - Any specific extraction instructions
   - Keep subagent outputs compact and structured (JSON preferred)
   - Store results using the REPL's `add_buffer()` function

6. **Synthesis**
   - Once enough evidence is collected, synthesize the final answer
   - Cite specific evidence (line numbers, timestamps, resource names)
   - Provide actionable recommendations

## SRE/DevOps Context-Specific Tips

### For Log Analysis
```python
# Find error patterns first
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(grep(r'(ERROR|FATAL|Exception)', max_matches=50))"

# Check for specific service issues
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(grep(r'service_name.*failed', max_matches=20))"
```

### For Kubernetes Manifests
```python
# Find all resource types
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(grep(r'^kind:\s*\w+', max_matches=100))"
```

### For Terraform State
```python
# Find resources by type
python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(grep(r'\"type\":\s*\"aws_', max_matches=50))"
```

## Guardrails

- Do not paste large raw chunks into the main chat context
- Use the REPL to locate exact excerpts; quote only what you need
- Subagents cannot spawn other subagents; orchestration stays in root
- Keep scratch/state files under `.opencode/rlm_state/`
- Clean up chunk files after analysis is complete
