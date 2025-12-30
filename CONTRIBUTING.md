# Contributing to Duty Bot

Thank you for your interest in contributing to Duty Bot! We welcome contributions from the community to help make this project better.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/duty_bot.git
   cd duty_bot
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Backend (Python)

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   python scripts/generate_security_keys.py --output .env.security
   cat .env.security >> .env
   rm .env.security
   ```

4. Run the backend:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend (React)

1. Install dependencies:
   ```bash
   cd webapp
   npm install
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

### Database Setup

Use Docker Compose to set up PostgreSQL:
```bash
docker-compose up -d postgres
```

Or use a local PostgreSQL installation and update `DATABASE_URL` in `.env`.

## Code Style & Standards

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
  - Use type hints where appropriate
  - Use meaningful variable and function names
  - Keep functions focused and reasonably sized

- **TypeScript/React**: Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
  - Use TypeScript for type safety
  - Use functional components with hooks
  - Keep components modular and reusable

### Code Quality Tools

- **Python**: Use `black` for formatting and `flake8` for linting
- **TypeScript**: Use `tsc` for type checking and `eslint` for linting

## Testing

### Running Tests

```bash
# Backend tests
pytest tests/

# Frontend type checking
cd webapp
npm run type-check
```

### Writing Tests

- Write tests for new features and bug fixes
- Aim for reasonable code coverage
- Test edge cases and error conditions
- Place tests in the `tests/` directory with matching structure to `app/`

## Commit Guidelines

- Use clear, descriptive commit messages
- Start with a verb: "Add", "Fix", "Improve", "Refactor", etc.
- Reference issues when applicable: `fixes #123`
- Keep commits atomic (one logical change per commit)

Example:
```
feat: Add Google Calendar integration for schedule syncing

- Implemented GoogleCalendarService for syncing duty schedules
- Added new API endpoints for calendar configuration
- Updated database models to support calendar sync status
fixes #45
```

## Pull Requests

1. **Before submitting:**
   - Ensure all tests pass
   - Run linters and formatters
   - Update documentation if needed
   - Rebase on latest `main` branch

2. **PR description should include:**
   - What changes were made and why
   - Related issues (closes #123)
   - Testing instructions
   - Screenshots (if UI changes)

3. **Review process:**
   - At least one maintainer review required
   - All CI checks must pass
   - Address review comments promptly

## Reporting Issues

When reporting bugs, please include:
- **Detailed description** of the issue
- **Steps to reproduce**
- **Expected behavior** vs. actual behavior
- **Environment**: OS, Python/Node version, etc.
- **Logs and error messages**
- **Screenshots** (if applicable)

## Feature Requests

- Check if the feature already exists or has been requested
- Describe the use case and expected behavior
- Explain why this feature would be valuable
- Discuss implementation approach (if you have ideas)

## Documentation

- Update README.md for user-facing changes
- Add/update docstrings for new functions
- Update SETUP_GUIDE.md for integration changes
- Update COMMANDS.md for new bot commands

## Areas for Contribution

- **Bug fixes**: Check the issue tracker for reported bugs
- **Documentation**: Improve guides, fix typos, add examples
- **Testing**: Increase test coverage, add edge case tests
- **Performance**: Optimize database queries, reduce API calls
- **Localization**: Add translations for more languages
- **Feature requests**: Check open issues for requested features

## Code of Conduct

Please review our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing. We are committed to providing a welcoming and inclusive environment.

## Questions?

- Open an issue with your question
- Check existing documentation and FAQs
- Reach out to maintainers in discussions

## License

By contributing to Duty Bot, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to make Duty Bot better! 🚀
