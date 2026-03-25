# Contributing to PC_Workman

## Code of Conduct

Be respectful. Focus on the problem, not the person.

## How to Contribute

### Reporting Issues

Found a bug or want to suggest a feature?

1. Check existing [issues](https://github.com/HuckleR2003/PC_Workman_HCK/issues)
2. Provide reproduction steps for bugs
3. Include your system specs (Windows version, CPU, GPU)
4. Attach logs from `data/logs/` if relevant

### Suggesting Features

1. Open a [discussion](https://github.com/HuckleR2003/PC_Workman_HCK/discussions) first
2. Describe the use case and expected behavior
3. Link related issues if applicable

### Submitting Pull Requests

#### Requirements

- Python 3.9+ code following the existing style
- Tests for new features (in `tests/` directory)
- Updated docstrings
- No breaking changes without discussion

#### Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test locally: `python startup.py`
5. Commit with clear messages: `git commit -m "Add specific feature description"`
6. Push and open a pull request

#### Code Style

Follow the existing patterns in the codebase:

- **Core modules** (`core/`): Background-threaded operations, no UI blocking
- **hck_GPT** (`hck_gpt/`): Command routing with local insights
- **Stats Engine** (`hck_stats_engine/`): SQLite operations with WAL mode
- **UI** (`ui/`): Tkinter widgets with reusable components

Use meaningful variable names and add comments for complex logic.

## Development Setup

```bash
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK

python -m venv venv
.\venv\Scripts\activate  # Windows

pip install -r requirements.txt
python startup.py
```

## Architecture Overview
`core/` – System monitoring with background threads
`hck_gpt/` – Local AI insights and command handling
`hck_stats_engine/` – SQLite-based data aggregation
`ui/` – Tkinter interface components
`data/` – Local logs and database storage

## Project Structure
1. Issues are tracked on the [project ROADMAP board](https://github.com/users/HuckleR2003/projects/3)
2. v2.0 milestone targets Microsoft Store release (Q3 2026)
3. Testing and documentation are high priorities

## Questions?
Open a [discussion](https://github.com/HuckleR2003/PC_Workman_HCK/discussions)
Email: [firmuga.marcin.s@gmail.com](mailto:firmuga.marcin.s@gmail.com)

## License
By contributing, you agree your work is licensed under MIT. See [LICENSE](https://github.com/HuckleR2003/PC_Workman_HCK/blob/main/LICENSE) for details.
