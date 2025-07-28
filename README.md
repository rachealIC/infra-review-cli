
# Infra Review CLI

Infra Review CLI is a command-line tool for scanning AWS infrastructure and 
identifying common issues across services like EC2, EBS, S3, ELB, 
and ECS. It surfaces security gaps, performance drifts, underutilized 
resources, and cost optimization opportunities — all with AI-powered
remediation suggestions and formatting options for reporting.

````

---

## Features

- Scan for:
  - Underutilized EC2 instances
  - Unattached EBS volumes
  - Publicly accessible S3 buckets
  - Unassociated Elastic IPs
  - Unused Load Balancers
  - ECS services not using the latest task definitions
- Identify findings across AWS Well-Architected Pillars
- Estimate potential monthly savings
- Auto-generate remediation steps using AI (Gemini/OpenAI fallback)
- Generate reports in text, JSON, or HTML
- Interactive CLI or flag-based automation support

---

## Installation

Install dependencies using [Poetry](https://python-poetry.org):

```bash
poetry install
````

Make sure your environment has AWS credentials set up (`~/.aws/credentials` or `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`).

---

## Usage

### Interactive Mode

```bash
poetry run python src/infra_review_cli/main.py
```

You’ll be guided through:

* Choosing a service (EC2, S3, ECS, ELB, etc.)
* Setting thresholds like CPU % or EBS age
* Selecting AWS region
* Choosing output format (text, JSON, HTML)
* Optionally saving to a report file

---

### Flag-Based Mode (Coming Soon)

```bash
poetry run cli check aws --region us-east-1 --format html --output report.html
```

---

## Output Formats

* **Text**: Plain, human-readable output in the terminal
* **JSON**: Machine-readable output for automation
* **HTML**: Styled report suitable for sharing or archiving

---

## AI Integration

Infra Review CLI uses Gemini (via Google Generative AI) or OpenAI to generate:

* Suggested remediation steps
* Estimated monthly savings (for cost optimization findings)

You can configure API keys via environment variables:

```bash
export GEMINI_API_KEY="your-google-key"
export OPENAI_API_KEY="your-openai-key"
```

---

## Project Structure

```
infra_review_cli/
├── adapters/         # AWS integrations, CLI adapter
├── core/             # Checks, enums, models, formatters
├── ai/               # Gemini/OpenAI fallback logic
├── reports/          # Summary + HTML/console views
├── main.py           # CLI entry point
```

---

## Supported Checks

| Check                                | Service | Pillar                 |
| ------------------------------------ | ------- | ---------------------- |
| EC2 underutilization                 | EC2     | Cost Optimization      |
| Unattached volumes                   | EBS     | Cost Optimization      |
| Unassociated Elastic IPs             | EC2     | Cost Optimization      |
| Public S3 buckets                    | S3      | Security               |
| Unused Load Balancers                | ELB     | Cost Optimization      |
| ECS not using latest task definition | ECS     | Performance Efficiency |

---

## Contributing


---

## License

MIT License


