# Career Sprint Agent

Personal career management system with MCP (Model Context Protocol) integration.

## Features

### Phase 1: Library Monitoring
- Track Python libraries for updates via PyPI API
- Detect breaking changes vs minor updates
- Learning integration (concepts by skill level)
- Local storage with JSON

### Future Phases
- Reading tracker (articles, papers, tutorials)
- Time tracking (projects vs work)
- Project tracker
- Full career dashboard
- MCP tools integration

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Check all libraries for updates
career-agent check-updates

# View current status
career-agent status

# View outdated libraries
career-agent outdated

# View learning opportunities
career-agent learn

# List monitored libraries
career-agent libraries

# View recent changes
career-agent changes --days 7

# Mark a library as updated
career-agent mark-updated torch
```

## Configuration

Edit `src/career_agent/config.py` to modify monitored libraries.

## MCP Integration (Coming Soon)

This agent will be deployable as an MCP server with tools:
- `get_library_status` - Get status of all monitored libraries
- `check_for_updates` - Check for new library versions
- `get_recent_changes` - Get changes detected in last N days
