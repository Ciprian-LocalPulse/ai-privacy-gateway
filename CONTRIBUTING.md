# Contributing to AI Privacy Gateway

Thank you for your interest in contributing to the **AI Privacy Gateway**! We welcome community contributions, bug reports, and feature requests to help make LLM integrations safer and compliant.

## ⚖️ A Note on Dual Licensing

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. By contributing to this repository, you agree that your contributions will be licensed under the same terms. The repository maintainers retain the right to dual-license the core codebase under commercial, non-copyleft terms for enterprise deployments.

## 🛠️ Local Development Setup

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/ai-privacy-gateway.git
   cd ai-privacy-gateway
   ```

2. **Set Up a Virtual Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Development Dependencies:**
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

## 📐 Code Quality & Standards

We enforce strict linting, type-checking, and formatting standards to keep the gateway robust:
* **Formatting:** `black` or `ruff format`
* **Linting:** `ruff check`
* **Type checking:** `mypy`

Before submitting a Pull Request, ensure all tests pass local checks:
```bash
pytest
mypy ai_privacy_gateway/
ruff check ai_privacy_gateway/
```

## 📥 Pull Request Guidelines

1. Create a descriptive branch: `git checkout -b feature/your-feature-name` or `bugfix/issue-id`.
2. Keep commits atomic and write clear commit messages.
3. Reference any related open issues in your Pull Request description.
4. Ensure your PR doesn't break asynchronous streaming performance.
