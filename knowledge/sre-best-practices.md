# SRE Best Practices Knowledge Base

## SLOs, SLIs, and Error Budgets

### SLI (Service Level Indicator)
Quantitative measure of service behavior:
- **Availability**: Successful requests / Total requests
- **Latency**: % of requests < threshold (e.g., p99 < 200ms)
- **Throughput**: Requests per second
- **Error Rate**: Failed requests / Total requests

### SLO (Service Level Objective)
Target value for an SLI over a time window:
- Availability SLO: 99.9% over 30 days
- Latency SLO: 99% of requests < 200ms

### Error Budget
Allowed unreliability = 1 - SLO
- 99.9% SLO = 0.1% error budget
- 30-day window = ~43 minutes of downtime allowed

### Error Budget Policy
```yaml
error_budget_remaining: ">50%"
actions:
  - Continue feature development normally

error_budget_remaining: "25-50%"
actions:
  - Prioritize reliability work
  - Review recent changes for risk

error_budget_remaining: "<25%"
actions:
  - Freeze non-critical deployments
  - Focus on reliability improvements
  - Conduct risk review for all changes
```

## Monitoring Strategy

### The Four Golden Signals
1. **Latency**: Time to service a request
2. **Traffic**: Demand on the system
3. **Errors**: Rate of failed requests
4. **Saturation**: How "full" the system is

### RED Method (Request-focused)
- **Rate**: Requests per second
- **Errors**: Failed requests per second
- **Duration**: Distribution of request latencies

### USE Method (Resource-focused)
- **Utilization**: % of time resource is busy
- **Saturation**: Amount of queued work
- **Errors**: Count of error events

## Alerting Best Practices

### Alert Quality
- Alert on symptoms, not causes
- Alerts should be actionable
- Every alert should have a runbook
- Avoid alert fatigue

### Alert Structure
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
for: 5m
labels:
  severity: critical
  team: platform
annotations:
  summary: High error rate detected
  description: Error rate is {{ $value | humanizePercentage }}
  runbook: https://runbooks.example.com/high-error-rate
  dashboard: https://grafana.example.com/d/errors
```

### Alert Routing
```yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: pagerduty-critical
    - match:
        severity: warning
      receiver: slack-warnings
```

## Deployment Strategies

### Rolling Update
- Gradual replacement of old pods
- Good for stateless applications
- Built into Kubernetes default

### Blue-Green
- Two identical environments
- Switch traffic atomically
- Easy rollback

### Canary
- Route small % of traffic to new version
- Monitor for issues
- Gradually increase traffic

### Feature Flags
- Deploy code without enabling feature
- Enable/disable features independently
- A/B testing capability

## Capacity Planning

### Key Metrics
- Current usage vs. limits
- Growth rate
- Seasonal patterns
- Lead time for provisioning

### Planning Formula
```
Required Capacity = Current Usage × Growth Factor × Safety Margin

Growth Factor = (1 + monthly_growth_rate) ^ months_ahead
Safety Margin = typically 1.3-1.5 (30-50% headroom)
```

## Chaos Engineering Principles

1. Start with a hypothesis about steady state
2. Introduce realistic failures
3. Run experiments in production (carefully)
4. Minimize blast radius
5. Automate experiments for continuous validation

### Common Experiments
- Pod termination
- Network latency injection
- Resource exhaustion
- Zone/region failures
- Dependency failures
