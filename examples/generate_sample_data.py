#!/usr/bin/env python3
"""
Generate sample data files for testing the RLM workflow.
Run this script to create test files in the context/ directory.

Usage:
    python3 examples/generate_sample_data.py
"""

import os
import random
import datetime
import json

# Ensure context directory exists
os.makedirs('context', exist_ok=True)

print("Generating sample data files for RLM testing...\n")

# =============================================================================
# 1. Application Log File
# =============================================================================
print("1. Creating sample_app.log...")

levels = ['INFO', 'INFO', 'INFO', 'INFO', 'WARN', 'ERROR', 'DEBUG']
services = ['api-gateway', 'user-service', 'order-service', 'payment-service', 'inventory-service']
messages = {
    'INFO': [
        'Request processed successfully',
        'Connection established',
        'Cache hit for key',
        'Health check passed',
        'Task completed',
        'User authenticated successfully',
        'Order created',
        'Payment processed',
        'Inventory updated'
    ],
    'WARN': [
        'High memory usage detected: 85%',
        'Slow query detected (>1s)',
        'Rate limit approaching: 80%',
        'Connection pool running low: 3 available',
        'Retry attempt 2/3',
        'Deprecated API version used',
        'Cache miss ratio high: 40%'
    ],
    'ERROR': [
        'Database connection failed: timeout after 30s',
        'Timeout waiting for response from downstream service',
        'NullPointerException in request handler',
        'Authentication failed: invalid token',
        'Service unavailable: circuit breaker open',
        'Out of memory error',
        'Connection refused to redis:6379',
        'SSL handshake failed'
    ],
    'DEBUG': [
        'Entering method processRequest',
        'Variable state: active=true, retries=0',
        'Query execution time: 45ms',
        'Cache miss for key: user_123',
        'HTTP request: GET /api/v1/users',
        'Response payload size: 2.3KB'
    ]
}

base_time = datetime.datetime.now() - datetime.timedelta(hours=3)
log_lines = []

for i in range(8000):
    ts = base_time + datetime.timedelta(seconds=i * 1.2 + random.uniform(0, 0.5))
    level = random.choice(levels)
    service = random.choice(services)
    msg = random.choice(messages[level])
    
    # Add request ID for tracing
    request_id = f"req-{random.randint(10000, 99999)}"
    
    log_line = f'{ts.isoformat()} [{level}] [{service}] [{request_id}] {msg}'
    log_lines.append(log_line)
    
    # Add stack trace for some errors
    if level == 'ERROR' and random.random() > 0.6:
        log_lines.append(f'    at com.example.{service.replace("-", ".")}.Handler.process(Handler.java:{random.randint(50,200)})')
        log_lines.append(f'    at com.example.{service.replace("-", ".")}.Service.execute(Service.java:{random.randint(100,300)})')
        log_lines.append(f'    at com.example.common.BaseController.handle(BaseController.java:{random.randint(30,80)})')
        if random.random() > 0.5:
            log_lines.append(f'Caused by: java.sql.SQLException: Connection timed out')
            log_lines.append(f'    at com.mysql.jdbc.ConnectionImpl.connect(ConnectionImpl.java:456)')

with open('context/sample_app.log', 'w') as f:
    f.write('\n'.join(log_lines))

print(f"   Created context/sample_app.log ({len(log_lines)} lines)")

# =============================================================================
# 2. Kubernetes Manifests
# =============================================================================
print("2. Creating k8s-manifests.yaml...")

k8s_manifests = '''---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: production
  labels:
    app: api-gateway
    version: v1.2.3
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
        version: v1.2.3
    spec:
      containers:
      - name: api-gateway
        image: myregistry/api-gateway:v1.2.3
        ports:
        - containerPort: 8080
          name: http
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
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: LOG_LEVEL
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
        # BAD PRACTICE: Hardcoded secret
        - name: DB_PASSWORD
          value: "super-secret-password-123"
        - name: DB_HOST
          value: "postgres.production.svc.cluster.local"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          # Missing limits - potential issue
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      containers:
      - name: payment-service
        image: myregistry/payment-service:latest
        # Using :latest tag - bad practice
        ports:
        - containerPort: 8082
        # Missing health probes
        # Missing resource limits
        securityContext:
          privileged: true  # Security issue!
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
    name: http
  type: LoadBalancer
---
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: production
spec:
  selector:
    app: user-service
  ports:
  - port: 8081
    targetPort: 8081
  type: ClusterIP
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
  MAX_CONNECTIONS: "100"
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
'''

with open('context/k8s-manifests.yaml', 'w') as f:
    f.write(k8s_manifests)

print("   Created context/k8s-manifests.yaml")

# =============================================================================
# 3. Terraform Plan JSON
# =============================================================================
print("3. Creating terraform-plan.json...")

terraform_plan = {
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
                    "values": {
                        "ami": "ami-0c55b159cbfafe1f0",
                        "instance_type": "t3.medium",
                        "tags": {
                            "Name": "web-server-prod",
                            "Environment": "production"
                        },
                        "root_block_device": {
                            "encrypted": False,  # Security issue
                            "volume_size": 50
                        }
                    }
                },
                {
                    "address": "aws_security_group.web_sg",
                    "mode": "managed",
                    "type": "aws_security_group",
                    "name": "web_sg",
                    "values": {
                        "name": "web-server-sg",
                        "description": "Security group for web servers",
                        "ingress": [
                            {
                                "description": "SSH from anywhere",
                                "from_port": 22,
                                "to_port": 22,
                                "protocol": "tcp",
                                "cidr_blocks": ["0.0.0.0/0"]  # Security issue!
                            },
                            {
                                "description": "HTTP",
                                "from_port": 80,
                                "to_port": 80,
                                "protocol": "tcp",
                                "cidr_blocks": ["0.0.0.0/0"]
                            },
                            {
                                "description": "All ports open",
                                "from_port": 0,
                                "to_port": 65535,
                                "protocol": "tcp",
                                "cidr_blocks": ["0.0.0.0/0"]  # Major security issue!
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
                        "bucket": "my-company-sensitive-data",
                        "acl": "public-read",  # Security issue!
                        "versioning": {
                            "enabled": False
                        },
                        "server_side_encryption_configuration": None  # Missing encryption
                    }
                },
                {
                    "address": "aws_db_instance.database",
                    "mode": "managed",
                    "type": "aws_db_instance",
                    "name": "database",
                    "values": {
                        "identifier": "prod-database",
                        "allocated_storage": 100,
                        "engine": "mysql",
                        "engine_version": "8.0",
                        "instance_class": "db.t3.large",
                        "publicly_accessible": True,  # Security issue!
                        "skip_final_snapshot": True,  # Data loss risk
                        "backup_retention_period": 0,  # No backups!
                        "storage_encrypted": False,  # Security issue
                        "multi_az": False  # No HA
                    }
                },
                {
                    "address": "aws_iam_role.admin_role",
                    "mode": "managed",
                    "type": "aws_iam_role",
                    "name": "admin_role",
                    "values": {
                        "name": "super-admin-role",
                        "assume_role_policy": json.dumps({
                            "Version": "2012-10-17",
                            "Statement": [{
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},  # Too permissive!
                                "Action": "sts:AssumeRole"
                            }]
                        })
                    }
                }
            ]
        }
    },
    "resource_changes": [
        {"address": "aws_instance.web_server", "change": {"actions": ["create"]}},
        {"address": "aws_security_group.web_sg", "change": {"actions": ["create"]}},
        {"address": "aws_s3_bucket.data", "change": {"actions": ["create"]}},
        {"address": "aws_db_instance.database", "change": {"actions": ["create"]}},
        {"address": "aws_iam_role.admin_role", "change": {"actions": ["create"]}}
    ]
}

with open('context/terraform-plan.json', 'w') as f:
    json.dump(terraform_plan, f, indent=2)

print("   Created context/terraform-plan.json")

# =============================================================================
# 4. JSONL Metrics Log
# =============================================================================
print("4. Creating metrics.jsonl...")

metrics_lines = []
base_time = datetime.datetime.now() - datetime.timedelta(hours=1)

for i in range(2000):
    ts = base_time + datetime.timedelta(seconds=i * 1.8)
    
    # Simulate metrics with occasional anomalies
    cpu_base = 45 + random.uniform(-10, 10)
    memory_base = 60 + random.uniform(-5, 5)
    
    # Add some anomalies
    if 500 < i < 600:  # CPU spike
        cpu_base = 85 + random.uniform(0, 10)
    if 800 < i < 900:  # Memory leak pattern
        memory_base = 60 + (i - 800) * 0.3
    
    error_rate = 0.01
    if 1200 < i < 1300:  # Error spike
        error_rate = 0.15 + random.uniform(0, 0.05)
    
    metric = {
        "timestamp": ts.isoformat(),
        "service": random.choice(services),
        "metrics": {
            "cpu_percent": round(cpu_base, 2),
            "memory_percent": round(min(memory_base, 95), 2),
            "request_count": random.randint(100, 500),
            "error_rate": round(error_rate, 4),
            "latency_p50_ms": random.randint(20, 80),
            "latency_p99_ms": random.randint(150, 500),
            "active_connections": random.randint(50, 200)
        }
    }
    metrics_lines.append(json.dumps(metric))

with open('context/metrics.jsonl', 'w') as f:
    f.write('\n'.join(metrics_lines))

print(f"   Created context/metrics.jsonl ({len(metrics_lines)} records)")

# =============================================================================
# Summary
# =============================================================================
print("\n" + "="*60)
print("Sample data generation complete!")
print("="*60)
print("\nCreated files:")
print("  - context/sample_app.log      (Application logs with errors)")
print("  - context/k8s-manifests.yaml  (K8s manifests with issues)")
print("  - context/terraform-plan.json (Terraform plan with security issues)")
print("  - context/metrics.jsonl       (Time-series metrics with anomalies)")
print("\nYou can now test RLM with commands like:")
print('  /rlm context=context/sample_app.log query="Find all errors"')
print('  /rlm context=context/k8s-manifests.yaml query="Find security issues"')
print('  /rlm context=context/terraform-plan.json query="Review for AWS best practices"')
