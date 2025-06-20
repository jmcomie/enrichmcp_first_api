# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EnrichMCP First API is a world-building application built with Python using the EnrichMCP framework, FastMCP, and Streamlit. The application provides an MCP (Model Context Protocol) server for creating and managing world-building entities with relationships, plus a Streamlit web UI for browsing the data.

## Architecture

**Core Components:**
- `enrichmcp_first_api/api.py` - Main MCP server with all resources and entities
- `enrichmcp_first_api/model.py` - Base WorldBuilderEntity class  
- `enrichmcp_first_api/streamlit_ui.py` - Web browser interface
- `enrichmcp_first_api/lib/logger.py` - Custom file logging utility

**Data Storage:**
- Projects stored in user data directory under `~/.local/share/enrichmcp_first_api/projects/`
- Each project contains `project.json` and a `models/` directory with generated Python model files
- Entity instances stored in `instances.json` within each project directory

**Model System:**
- Dynamic model creation - users create entity types through MCP calls
- Models are written as Python files and dynamically imported
- Relationships between entities are supported (one-to-one, one-to-many, etc.)
- All models inherit from `WorldBuilderEntity` base class

## Development Commands

**Run MCP Server:**
```bash
python -m enrichmcp_first_api.api
```

**Run Streamlit UI:**
```bash
streamlit run enrichmcp_first_api/streamlit_ui.py
```

**Install Dependencies:**
```bash
poetry install
```

**Run Python Module:**
```bash
poetry run python -m enrichmcp_first_api.api
```

## Key Patterns

**Project Workflow:**
1. Create or open a project (required first step)
2. Create entity types using `create_world_builder_entity` 
3. Add relationships between entities using `add_relationship_to_entity_schema`
4. Create instances using `create_world_builder_entity_instance`
5. Link instances with `add_relationship_between_instances`

**Entity Creation:**
- Models are dynamically generated and written to `{project}/models/{ModelName}.py`
- Each model file contains a single class inheriting from `WorldBuilderEntity`
- Models are imported and registered with the MCP app using decorators

**Relationship System:**
- Schema-level relationships define cardinality between entity types
- Instance-level relationships link specific entity instances
- Relationship fields marked with `FORWARD_REF_SEMAPHORE` in descriptions
- Bidirectional relationships are automatically maintained

**Global State Management:**
- `CURRENT_OPEN_PROJECT` tracks the active project
- `MODELS` list contains all registered entity classes
- `LAST_INSERTED_INSTANCE_ID` and `LAST_UPDATED_INSTANCE_ID` for tracking operations

**Error Handling:**
- Most operations return `Optional[ErrorResponse]` or `Optional[Notice]`
- Comprehensive logging using custom `FileLogger` class
- Model validation through Pydantic with detailed error messages