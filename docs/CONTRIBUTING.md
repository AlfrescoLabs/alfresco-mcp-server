# Contributing to Alfresco MCP Server

Thank you for your interest in contributing to this project. Your participation helps the community and makes the integration with Alfresco Content Services better for everyone.

## Project overview  

This project implements a Python-based server for the Model Context Protocol (MCP) focused on Alfresco Content Services. It allows AI agents or other clients to invoke tools and resources (search, upload, download, metadata management, etc.) against an Alfresco repository through the MCP interface.

## Ways to contribute  

- Report bugs or regressions.  
- Suggest enhancements or new tools for the MCP interface.  
- Submit pull requests for bug fixes, new features, documentation improvements.  
- Improve or extend examples, tests, and usage guides.  
- Help review issues or pull requests from others.

Before starting work, it’s good practice to check whether an issue already exists for your change. If not, please open one, describing the problem or enhancement you intend to implement.

## Development setup

### Prerequisites  

- Python 3.10+  
- An instance of Alfresco Content Services (Community or Enterprise) for integration-testing.  
- Familiarity with the MCP protocol and the specific tools exposed by this server.

### Getting started

```bash
git clone https://github.com/AlfrescoLabs/alfresco-mcp-server.git
cd alfresco-mcp-server
python -m venv .venv
source .venv/bin/activate    # or Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running & testing

* Run the server (see `README.md` for command-line options for transport, host, port).
* For integration tests you’ll need a running Alfresco repository and possibly additional configuration (see docs).

## Pull request process

1. Fork the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-tool
   ```
2. Write tests (unit and/or integration) for your change.
3. Ensure all new code follows existing style (PEP8, typing, documentation).
4. Run the full test suite and confirm everything passes.
5. Push your branch and open a Pull Request (targeting the `main` or equivalent branch).
6. In your PR description include:
   * A summary of the change.
   * Reference to the related issue (if any).
   * Any breaking changes or impacts for users.
7. Maintainers will review, comment, and merge when ready.

Small, focused PRs are easier to review and merge, prefer incremental changes rather than one large monolith.

## Code style & best practices

* Follow Python idioms (PEP8, typing, docstrings).
* Keep modules focused and functions well-documented.
* Use meaningful commit messages, e.g. "Add tool `search_by_metadata` for MCP".
* Write tests for new functionality and ensure coverage where applicable.
* Maintain backwards-compatibility when feasible; if breaking changes are required, clearly document them.

## Testing guidelines

* Use pytest for unit tests.
* Integration tests should target real Alfresco repository instances.
* If mocking Alfresco API, ensure core behaviours are covered.
* Include tests for error/edge cases (e.g., repository not reachable, invalid credentials).
* If adding new MCP tools, include both happy-path and failure cases.

## Reporting issues

If you encounter a bug or want to propose an enhancement:

* Check existing open issues to avoid duplication.
* Open a new issue with:
  * A clear and descriptive title.
  * Detailed steps to reproduce (if a bug).
  * Expected vs actual behaviour.
  * Relevant logs, stack traces or configuration snippets.
* For enhancement requests, describe the use-case, the benefit, and any API impact.

## Licence & contributor agreement

By contributing, you agree that your contributions will be licensed under the project’s license, which is the **Apache License 2.0**.
No separate Contributor License Agreement (CLA) is required unless otherwise indicated.

## Community & communication

This project is maintained by the AlfrescoLabs community.
You can participate via:

* GitHub issues and pull requests
* GitHub Discussions (if enabled)
* Mailing lists or community forums related to Alfresco / MCP

## Additional notes

* Update documentation (`docs/` directory) for any new features, usage instructions, or configuration changes.
* If you add new dependencies, justify them and ensure they align with project goals (minimal, well-maintained).

> Thank you for helping improve the Alfresco MCP Server: your contribution matters!
