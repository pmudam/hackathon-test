# AI Root Cause Assistant for Splunk

**Your problem:** When a threshold breach fires in Splunk, engineers manually correlate signals and diagnose the issue—slow, error-prone, and inefficient.

**Our solution:** Automated root cause analysis that correlates Splunk detector incidents and dashboard thresholds, identifies the probable root cause, and sends actionable remediation steps to Webex—all in one command.

---

## 🎯 What it does

1. **Detects incidents**: Fetches live incidents from your Splunk Observability detector.
2. **Correlates signals**: Normalizes and correlates threshold breaches with historical patterns.
3. **Identifies root cause**: Rule-based engine classifies probable causes (e.g., DynamoDB read capacity saturation).
4. **Recommends fixes**: Produces confidence-scored remediation steps with evidence timeline.
5. **Notifies in real time**: Posts detailed RCA summaries to Webex every check interval.

---

## 🚀 One-command demo

**Setup:**
```bash
cd /Users/prashanth/Documents/hackathon
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
# Edit .env and terraform.tfvars with your Splunk API credentials and Webex bot token
```

**Run (continuous monitoring + provisioning):**
```bash
make all-auto
```

This will:
- Provision a Splunk detector via Terraform
- Start a live monitoring loop (fetches incidents every 60 seconds by default)
- Send RCA results to your Webex space

**Or run once (manual RCA):**
```bash
make live-rca
```

---

## 📊 Example output

When a threshold breach occurs and incidents are fetched:

```
=== AI Root Cause Assistant ===
Affected service : piam-preview-dynamodb
Probable cause   : DynamoDB read capacity saturation
Confidence       : 0.92

Explanation:
- Read capacity utilization crossed policy thresholds and remained elevated.

Evidence:
- WARN threshold (>90%) sustained for 2m
- ALERT threshold (>95%) sustained for 2m

Suggested actions:
- Increase table read capacity or auto scaling limits
- Investigate hot partitions and rebalance access patterns
```

**Webex message (auto-posted every interval):**
```
**Splunk RCA Update**

**Service:** piam-preview-dynamodb
**Probable Cause:** DynamoDB read capacity saturation
**Confidence:** 0.92

**Explanation:**
Read capacity utilization crossed policy thresholds and remained elevated.

**Evidence:**
- WARN threshold (>90%) sustained for 2m
- ALERT threshold (>95%) sustained for 2m

**Suggested Actions:**
- Increase table read capacity or auto scaling limits
- Investigate hot partitions and rebalance access patterns
```

---

## 🏗️ Architecture

| Component | Purpose |
|-----------|---------|
| `Terraform (Splunk)` | Provisions detector + alert rules |
| `Python RCA Engine` | Correlates signals, infers root cause |
| `Splunk API Client` | Fetches live incidents |
| `Webex Bot` | Real-time notifications to teams |
| `Makefile` | One-command provisioning + monitoring |

---

## 📁 Key files

- `src/rca_assistant/cli.py` - command-line interface
- `src/rca_assistant/engine.py` - root-cause inference engine
- `src/rca_assistant/splunk_client.py` - live Splunk API integration
- `src/rca_assistant/continuous_rca.py` - monitoring loop + Webex notifications
- `src/rca_assistant/webex_utils.py` - Webex bot integration
- `infra/terraform/splunk_detector.tf` - Splunk detector definition
- `Makefile` - provisioning and monitoring targets

---

## ✅ Testing

```bash
make test
```

All tests pass (8/8). Terraform validates successfully.

---

## 🎓 Why this works for hackathons

1. **Real problem**: Threshold correlation is manual and error-prone today.
2. **Real solution**: Automated, confidence-scored RCA with evidence trails.
3. **Operational**: Truly works—tested, provisioned via Terraform, integrated with Splunk + Webex.
4. **Scalable**: Extend to custom thresholds, add ML ranking, integrate Slack/PagerDuty.
5. **One command**: `make all-auto` is all judges need to see it work.

---

## 🔒 Security

- Keep `splunk_auth_token` only in local `.env` or secrets manager.
- Webex bot token never committed to source control.
- RCA is advisory; engineers validate before action.

---

## Next steps (roadmap)

1. Add LLM explanation layer (Claude/GPT) with guardrails.
2. Integrate feedback loop (`correct/incorrect`) to improve ranking.
3. Add Slack/PagerDuty notifications.
4. Support custom dashboard DSLs beyond DynamoDB.
5. Embedding-based historical incident similarity.
