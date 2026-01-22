# RLM Usage Guide - Copy-Paste Examples

This guide provides ready-to-use examples for the RLM (Recursive Language Model) workflow in OpenCode.

---

## Quick Start

### Step 1: Generate Sample Data (Optional)

If you don't have a large file to analyze, create a sample log file:

```bash
# Generate sample application log (run in terminal first)
python3 -c "
import random
import datetime

levels = ['INFO', 'INFO', 'INFO', 'INFO', 'WARN', 'ERROR', 'DEBUG']
services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
messages = {
    'INFO': ['Request processed successfully', 'Connection established', 'Cache hit', 'Health check passed', 'Task completed'],
    'WARN': ['High memory usage detected', 'Slow query detected (>1s)', 'Rate limit approaching', 'Connection pool running low', 'Retry attempt'],
    'ERROR': ['Database connection failed', 'Timeout waiting for response', 'NullPointerException in handler', 'Authentication failed', 'Service unavailable'],
    'DEBUG': ['Entering method processRequest', 'Variable state: active=true', 'Query execution time: 45ms', 'Cache miss for key: user_123']
}

base_time = datetime.datetime.now() - datetime.timedelta(hours=2)
with open('context/sample_app.log', 'w') as f:
    for i in range(5000):
        ts = base_time + datetime.timedelta(seconds=i*1.5)
        level = random.choice(levels)
        service = random.choice(services)
        msg = random.choice(messages[level])
        if level == 'ERROR' and random.random() > 0.7:
            f.write(f'{ts.isoformat()} [{level}] [{service}] {msg}\n')
            f.write(f'    at com.example.{service.replace(\"-\", \".\")}.Handler.process(Handler.java:{random.randint(50,200)})\n')
            f.write(f'    at com.example.{service.replace(\"-\", \".\")}.Service.execute(Service.java:{random.randint(100,300)})\n')
        else:
            f.write(f'{ts.isoformat()} [{level}] [{service}] {msg}\n')
print('Created context/sample_app.log with 5000+ log entries')
"
```

---

## Example 1: Basic RLM Workflow

Copy and paste this entire block into OpenCode:

```
/rlm context=context/sample_app.log query="Find all ERROR level logs, identify the most common error patterns, and determine which service has the most errors"
```

---

## Example 2: Step-by-Step Manual RLM

If you prefer to run the RLM workflow manually, follow these steps:

### Step 2a: Initialize the REPL

```
Initialize the RLM REPL with my log file:

python3 .opencode/skills/rlm/scripts/rlm_repl.py init context/sample_app.log
python3 .opencode/skills/rlm/scripts/rlm_repl.py status
```

### Step 2b: Scout the Content

```
Show me the first 2000 characters of the log file to understand its format:

python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(peek(0, 2000))"
```

### Step 2c: Get Statistics

```
Get statistics about the log file:

python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(stats())"
```

### Step 2d: Search for Errors

```
Find all ERROR level log entries:

python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "print(grep(r'\[ERROR\]', max_matches=30))"
```

### Step 2e: Create Chunks (for very large files)

```
Split the log file into chunks for detailed analysis:

python3 .opencode/skills/rlm/scripts/rlm_repl.py exec -c "paths = write_chunks('.opencode/rlm_state/chunks', size=100000); print(f'Created {len(paths)} chunks'); print(paths)"
```

### Step 2f: Analyze a Chunk with Subagent

```
@rlm-subcall Please analyze the chunk at .opencode/rlm_state/chunks/chunk_0000.txt

Query: Find all errors, identify patterns, and note any stack traces. Return structured JSON with your findings.
```

### Step 2g: Clean Up

```
Clean up the RLM state when done:

python3 .opencode/skills/rlm/scripts/rlm_repl.py reset
```

---

## Example 3: Kubernetes Manifest Analysis

### Generate Sample K8s Manifests

```bash
# Run in terminal to create sample manifests
cat > context/k8s-manifests.yaml << 'EOF'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: myregistry/api-gateway:v1.2.3
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
      - name: user-service
        image: myregistry/user-service:v2.0.0
        ports:
        - containerPort: 8081
        env:
        - name: DB_PASSWORD
          value: "hardcoded-password-bad-practice"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: production
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  LOG_LEVEL: "DEBUG"
  API_TIMEOUT: "30s"
  ENABLE_TRACING: "true"
EOF
echo "Created context/k8s-manifests.yaml"
```

### Analyze K8s Manifests with RLM

```
/rlm context=context/k8s-manifests.yaml query="Review these Kubernetes manifests for security issues, missing best practices, and potential problems. Check for: hardcoded secrets, missing resource limits, missing probes, and security contexts."
```

---

## Example 4: Terraform State Analysis

### Generate Sample Terraform Output

```bash
# Run in terminal to create sample terraform plan output
cat > context/terraform-plan.json << 'EOF'
{
  "format_version": "1.0",
  "terraform_version": "1.5.0",
  "planned_values": {
    "root_module": {
      "resources": [
        {
          "address": "aws_instance.web_server",
          "mode": "managed",
          "type": "aws_instance",
          "name": "web_server",
          "provider_name": "registry.terraform.io/hashicorp/aws",
          "schema_version": 1,
          "values": {
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t3.medium",
            "tags": {
              "Name": "web-server-prod",
              "Environment": "production"
            },
            "vpc_security_group_ids": ["sg-12345678"]
          }
        },
        {
          "address": "aws_security_group.allow_all",
          "mode": "managed",
          "type": "aws_security_group",
          "name": "allow_all",
          "provider_name": "registry.terraform.io/hashicorp/aws",
          "values": {
            "name": "allow-all-traffic",
            "description": "Allow all inbound traffic",
            "ingress": [
              {
                "from_port": 0,
                "to_port": 65535,
                "protocol": "tcp",
                "cidr_blocks": ["0.0.0.0/0"]
              }
            ],
            "egress": [
              {
                "from_port": 0,
                "to_port": 0,
                "protocol": "-1",
                "cidr_blocks": ["0.0.0.0/0"]
              }
            ]
          }
        },
        {
          "address": "aws_s3_bucket.data",
          "mode": "managed",
          "type": "aws_s3_bucket",
          "name": "data",
          "values": {
            "bucket": "my-company-data-bucket",
            "acl": "public-read"
          }
        },
        {
          "address": "aws_rds_instance.database",
          "mode": "managed",
          "type": "aws_db_instance",
          "name": "database",
          "values": {
            "allocated_storage": 100,
            "engine": "mysql",
            "engine_version": "8.0",
            "instance_class": "db.t3.large",
            "publicly_accessible": true,
            "skip_final_snapshot": true,
            "backup_retention_period": 0
          }
        }
      ]
    }
  },
  "resource_changes": [
    {
      "address": "aws_instance.web_server",
      "change": {
        "actions": ["create"]
      }
    },
    {
      "address": "aws_security_group.allow_all",
      "change": {
        "actions": ["create"]
      }
    },
    {
      "address": "aws_s3_bucket.data",
      "change": {
        "actions": ["create"]
      }
    },
    {
      "address": "aws_rds_instance.database",
      "change": {
        "actions": ["create"]
      }
    }
  ]
}
EOF
echo "Created context/terraform-plan.json"
```

### Analyze Terraform Plan

```
/rlm context=context/terraform-plan.json query="Review this Terraform plan for security issues and AWS best practices. Check for: overly permissive security groups, public S3 buckets, publicly accessible databases, missing encryption, and backup configurations."
```

---

## Example 5: Using Specialized Agents

### Kubernetes Debugging

```
@k8s-expert My pods are in CrashLoopBackOff state. Help me debug:

kubectl get pods -n production
kubectl describe pod api-gateway-xxx -n production
kubectl logs api-gateway-xxx -n production --previous
```

### Terraform Review

```
@terraform-expert Review my Terraform configuration for the VPC module. Check for security best practices and suggest improvements.
```

### Log Analysis

```
@log-analyzer Analyze the application logs in context/sample_app.log. Find error patterns, identify the timeline of issues, and suggest root causes.
```

### Podman Debugging

```
@podman-expert My container keeps restarting. Help me debug:

podman ps -a
podman logs mycontainer
podman inspect mycontainer
```

---

## Example 6: Incident Response Workflow

```
/incident Production API returning 503 errors

Recent observations:
- Started approximately 15 minutes ago
- Affecting /api/v1/users endpoint
- Error rate jumped from 0.1% to 15%
- No recent deployments in the last 2 hours
```

---

## Example 7: Generate Runbook

```
/runbook Database failover procedure

Context:
- Primary database: PostgreSQL on AWS RDS
- Replica in different AZ
- Applications connect via connection pooler (PgBouncer)
```

---

## Example 8: Create Postmortem

```
/postmortem 2024-01-15 API Gateway Outage

Details:
- Duration: 45 minutes
- Impact: 30% of API requests failed
- Root cause: Memory leak in new release
- Resolution: Rollback to previous version
```

---

## REPL Helper Functions Reference

| Function | Description | Example |
|----------|-------------|---------|
| `peek(start, end)` | View slice of content | `peek(0, 1000)` |
| `grep(pattern, max_matches)` | Search with regex | `grep(r'ERROR', 20)` |
| `grep_count(pattern)` | Count occurrences | `grep_count(r'ERROR')` |
| `find_lines(pattern)` | Find lines with numbers | `find_lines(r'Exception')` |
| `stats()` | Content statistics | `stats()` |
| `time_range()` | Extract time range | `time_range()` |
| `chunk_indices(size, overlap)` | Get chunk boundaries | `chunk_indices(100000, 1000)` |
| `write_chunks(dir, size)` | Write chunks to files | `write_chunks('.opencode/rlm_state/chunks', 100000)` |
| `add_buffer(text)` | Store intermediate results | `add_buffer('finding 1')` |
| `extract_json_objects()` | Parse JSONL content | `extract_json_objects()` |
| `extract_yaml_documents()` | Split YAML docs | `extract_yaml_documents()` |

---

## Tips

1. **Start with stats()**: Always check `stats()` first to understand your file size and content
2. **Scout before chunking**: Use `peek()` to understand the format before deciding chunk size
3. **Use grep for targeting**: Find specific patterns before doing full analysis
4. **Clean up after**: Run `reset` to clean up chunk files when done
5. **Use appropriate agents**: `@log-analyzer` for logs, `@k8s-expert` for K8s, etc.
