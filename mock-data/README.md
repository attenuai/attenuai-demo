# Mock data

This folder drives the three-act demo:

- `act1_*` contains only benign data
- `act2_*` introduces malicious payloads
- the agent switches datasets with `CURRENT_ACT`

## Attack payloads

- `act2_inbox.json`: external vendor email hides a forwarding instruction
- `act2_calendar.json`: external invite hides a rejection-message exfil instruction
- `content-server/pages/mal-ai-trends.html`: hidden CSS text instructs the agent to read a local file and exfiltrate it
