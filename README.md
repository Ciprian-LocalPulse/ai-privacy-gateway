# AI Privacy Gateway
<a href="https://github.com/Ciprian-LocalPulse/ai-privacy-gateway">
  <img src="assets/baner.png" alt="AI Privacy Gateway Banner" style="width:100%;">
</a>

> Enterprise-grade AI Privacy Gateway for secure, provider-agnostic LLM access.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-AGPL%20v3-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## Overview

AI Privacy Gateway is a middleware layer that sits between client applications and Large Language Models (LLMs), automatically protecting sensitive information before requests leave your infrastructure.

The gateway anonymizes Personally Identifiable Information (PII), routes requests to multiple AI providers through a unified interface, and restores protected data after responses are received.

The project is designed for enterprise environments where privacy, compliance, and provider independence are essential.

---

## Features

- Automatic PII detection
- Data anonymization before transmission
- Re-identification of protected data
- Multi-provider routing
- Provider abstraction layer
- OpenAI support
- Anthropic support
- Azure OpenAI support
- Async architecture
- Streaming support
- Provider-agnostic API
- Extensible adapter system
- Enterprise-ready design

---

## Architecture

```
Application
      │
      ▼
AI Privacy Gateway
      │
 ┌────┴────┐
 │PII Scan │
 └────┬────┘
      ▼
Anonymization
      ▼
Provider Router
      ▼
OpenAI / Anthropic / Azure OpenAI
      ▼
Response
      ▼
Re-identification
      ▼
Application
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/yourusername/ai-privacy-gateway.git
```

Enter the project

```bash
cd ai-privacy-gateway
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Configure your provider credentials through environment variables.

Example:

```env
OPENAI_API_KEY=

ANTHROPIC_API_KEY=

AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=
```

---

## Supported Providers

- OpenAI
- Anthropic
- Azure OpenAI

Additional providers can be implemented by extending the `LLMProvider` interface.

---

## Project Structure

```
ai_privacy_gateway/

├── providers/
│   ├── base.py
│   ├── router.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── azure_openai_provider.py
│
├── gateway/
├── anonymizer/
├── config/
└── utils/
```

---

## Design Principles

- Privacy by Design
- Provider Independence
- Security First
- Async Performance
- Clean Architecture
- Extensible Components

---

## Use Cases

- Enterprise AI
- Healthcare
- Financial Services
- Legal AI
- Government
- Internal AI Assistants
- Secure Chatbots
- Compliance Workflows

---

## Requirements

- Python 3.11+
- AsyncIO
- OpenAI SDK
- Anthropic SDK
- httpx

---

## Contributing

Pull requests are welcome.

Please open an issue first to discuss major changes before submitting a PR.

---

## Security

If you discover a security vulnerability, please report it privately before opening a public issue.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0).**

See the LICENSE file for details.
