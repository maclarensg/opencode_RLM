# Incident Response Knowledge Base

## Severity Levels

| Level | Name | Response Time | Examples |
|-------|------|---------------|----------|
| SEV1 | Critical | Immediate | Complete outage, data loss, security breach |
| SEV2 | High | 15 minutes | Major feature unavailable, significant degradation |
| SEV3 | Medium | 1 hour | Minor feature issues, non-critical service degraded |
| SEV4 | Low | Next business day | Cosmetic issues, minor bugs |

## Incident Response Workflow

### 1. Detection & Triage
- Acknowledge the alert
- Assess initial severity
- Start incident channel/war room if SEV1/SEV2
- Assign incident commander

### 2. Investigation
- Gather context: recent deployments, changes, metrics
- Check dashboards and logs
- Identify affected systems and scope
- Correlate events across services

### 3. Mitigation
- Prioritize restoring service over root cause
- Consider rollback if recent deployment
- Scale resources if capacity issue
- Enable circuit breakers/feature flags
- Communicate status updates

### 4. Resolution
- Confirm service is restored
- Verify metrics have returned to normal
- Document timeline and actions taken
- Schedule postmortem

### 5. Follow-up
- Conduct blameless postmortem
- Create action items
- Update runbooks
- Improve monitoring/alerting

## Common Mitigation Strategies

### Rollback
```bash
# Kubernetes rollback
kubectl rollout undo deployment/<name>

# Helm rollback
helm rollback <release> <revision>

# Feature flag disable
# [Use your feature flag system]
```

### Scale Up
```bash
# Kubernetes scale
kubectl scale deployment/<name> --replicas=<n>

# HPA adjustment
kubectl patch hpa <name> -p '{"spec":{"minReplicas":<n>}}'
```

### Traffic Management
```bash
# Drain node
kubectl drain <node> --ignore-daemonsets

# Block traffic at ingress
kubectl annotate ingress <name> nginx.ingress.kubernetes.io/whitelist-source-range="0.0.0.0/32"
```

## Communication Templates

### Initial Notification
```
[INCIDENT] SEV<N> - <Brief Description>
Impact: <Who/what is affected>
Status: Investigating
Next Update: <time>
```

### Status Update
```
[UPDATE] SEV<N> - <Brief Description>
Current Status: <Investigating/Mitigating/Monitoring>
Actions Taken: <List of actions>
Next Steps: <Planned actions>
Next Update: <time>
```

### Resolution
```
[RESOLVED] SEV<N> - <Brief Description>
Duration: <start time> - <end time>
Resolution: <What fixed it>
Follow-up: Postmortem scheduled for <date>
```
