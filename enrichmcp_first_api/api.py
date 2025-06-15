from __future__ import annotations
from datetime import date
import os
from typing import Optional
from altair import Type
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import Field
import base64
from io import BytesIO
from appdirs import user_data_dir
from pathlib import Path
import logging
import enrichmcp_first_api
from enrichmcp_first_api.lib.logger import FileLogger
import importlib
import sys
import importlib.util
# Create the application
app = EnrichMCP(title="WorldBuilder", description="A simple API for world building and creating new character classes, buildings, towns, and relationships. A project must always be opened before any models are created or modified.")
MODELS_DIRECTORY: Path = Path(f"{enrichmcp_first_api.__path__[0]}/models")
PROJECT_FILE_NAME: str = "project.json"


MODELS: list[Type[EnrichModel]] = []


def get_path_to_project(project_id: str) -> str:
    """
    Get the path to the project directory based on the project ID.
    This is used to store project-specific data.
    """
    project_path: Path = Path(f"{get_app_dir()}/projects/{project_id}")
    if not project_path.exists():
        project_path.mkdir(parents=True, exist_ok=True)
    return project_path


def project_exists(project_id: str) -> bool:
    """
    Check if a project exists by its ID.
    """
    project_path: Path = Path(f"{get_app_dir()}/projects/{project_id}")
    return project_path.exists()


# Use module root directory as log file directory
LOG: FileLogger =  FileLogger(
    log_file=f"{enrichmcp_first_api.__path__[0]}/logs/enrichmcp_first_api.log",
    level=logging.INFO,
    domain="EnrichMCPFirstAPI"
)

def get_model_path(model_name: str) -> str:
    if CURRENT_OPEN_PROJECT is None:
        raise ValueError("No project is currently open. Please open a project before accessing models.")
    project_path: Path = Path(get_path_to_project(CURRENT_OPEN_PROJECT.id))
    model_path: Path = project_path / "models" / f"{model_name}.py"
    return model_path


def get_app_dir() -> str:
    """
    Get the directory where the application is running.
    This is used to store logs and other files.
    """
    return user_data_dir("enrichmcp_first_api")


@app.entity(description="A project in the EnrichMCP system. A project is a collection of models, relationships, and other data that can be used to build a world.")
class Project(EnrichModel):
    id: str = Field(description="Unique identifier for the project")
    name: str = Field(description="Name of the project")
    theme: str = Field(description="Theme of the project -- this informs the creation of new models and relationships.")

CURRENT_OPEN_PROJECT: Optional[Project] = None


@app.entity(description="A model field in the EnrichMCP system. This is used to define the fields of a pydantic model that can be used in the current project.")
class ModelField(EnrichModel):
    name: str = Field(description="The name of the field in the model.")
    type: str = Field(description="The type of the field. Supported types are str, int, float, bool, date.")
    description: str = Field(description="A description of the field.")


def model_string_from_fields(name: str, model_fields: list[ModelField]) -> str:
    """
    Add a model to the EnrichMCP application.
    This is used to register models that can be used in the current project.
    """
    # iterate over the fields and create a string representation of the model
    model_str: str = f"""\
from enrichmcp import EnrichMCP, EnrichModel
from pydantic import Field

class {name}(EnrichModel):
    \"\"\"A pydantic model named {name} with fields: {', '.join([field.name for field in model_fields])}.\"\"\"
"""
    for field in model_fields:
        model_str += f"    {field.name}: {field.type} = Field(description=\"{field.description}\")\n"
    model_str += "\n"
    return model_str



def import_module_from_path(module_name, module_path):
    """Imports a module from a given file path and applies entity decorators to all classes."""
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Module file not found: {module_path}")
    
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for module '{module_name}' from '{module_path}'")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Optional: only if global/module cache needed
    spec.loader.exec_module(module)
    
    # Apply entity decorator to all classes in the module
    for name in dir(module):
        obj = getattr(module, name)
        # Check if it's a class and not a built-in/imported class
        if (isinstance(obj, type) and 
            obj.__module__ == module_name and 
            hasattr(obj, '__doc__') and 
            obj.__doc__):
            # Apply the decorator manually
            decorated_class = app.entity(obj)
            setattr(module, name, decorated_class)
    
    return module


def write_model_to_file_and_import(model_name: str, model_fields: list[ModelField]) -> None:
    """
    Write the model to a file in the current project directory.
    This is used to persist the model definition.
    """
    LOG.info(f"Writing model {model_name} with fields: {model_fields}")
    model_path: Path = get_model_path(model_name)
    if not model_path.parent.exists():
        model_path.parent.mkdir(parents=True, exist_ok=True)
    if model_path.exists():
        LOG.warning(f"Model file {model_path} already exists. It will be overwritten.")
    model_str: str = model_string_from_fields(model_name, model_fields)
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write(model_str)
    LOG.info(f"Model {model_name} written to {model_path}")
    try:
        importlib.invalidate_caches()  # Clear the import cache
        # import model_path
        import_module_from_path(model_name, model_path)
    except Exception as e:
        LOG.error(f"Error importing model {model_name} from {model_path}: {e}")
        raise ImportError(f"Error importing model {model_name} from {model_path}: {e}")


@app.resource(description="This is an optional error response. If an error occurs, attempt correct and call tool again")
class ErrorResponse(EnrichModel):
    error: str = Field(description="A description of the error that occurred.")


@app.resource(description="Create a new pydantic model based on the current open project theme. Never call unless expressly directed by the user.")
async def create_model(name: str, fields: list[ModelField]) -> Optional[ErrorResponse]:
    """Create a pydantic model specified by a name, and a list of lists containing
     the field name, the field type, and the description.   Ensure that each field
     contains the field name, the field type, and the description.
     Call explore data model after this to explore the data model and
     see the new model."""
    LOG.info(f"Creating model {name} with fields: {fields}")
    try:
        write_model_to_file_and_import(name, fields)
    except Exception as e:
        LOG.exception(f"Error creating model {name}: {e}")
        return ErrorResponse(error=f"Error creating model {name}: {e}; provide this error to user.")
    LOG.info(f"Model {name} created successfully.")


@app.resource(description="List all available models in the EnrichMCP system. This is used to get a list of all models that can be used in the current project.")
async def list_models() -> list[Type[EnrichModel]]:
    return MODELS


@app.resource(description="Create a new project. This or opening an existing project must be done before any models are created or modified. A project is a collection of models, relationships, and other data that can be used to build a world.")
async def create_new_project(project: Project) -> Project:
    if project_exists(project.id):
        LOG.error(f"Project with ID {project.id} already exists.")
        raise ValueError(f"Project with ID {project.id} already exists.")
    project_path: Path = Path(f"{get_app_dir()}/projects/{project.id}")
    if not project_path.exists():
        project_path.mkdir(parents=True, exist_ok=True)
    project_file: Path = project_path / PROJECT_FILE_NAME
    with open(project_file, 'w', encoding='utf-8') as f:
        f.write(project.model_dump_json(indent=4))
    LOG.info(f"Project {project.name} created with ID {project.id}.")
    global CURRENT_OPEN_PROJECT
    CURRENT_OPEN_PROJECT = project
    return project


@app.resource(description="List all projects in the EnrichMCP system. This is used to get a list of all projects that can be opened or modified.")
def list_projects() -> list[Project]:
    project_path = Path(get_app_dir()) / "projects"
    if not project_path.exists():
        LOG.warning("No projects directory found. Returning empty project list.")
        return []

    projects = []
    for project_dir in project_path.iterdir():
        project_file_path = project_dir / PROJECT_FILE_NAME
        if not project_file_path.exists():
            LOG.warning(f"Skipping non-project directory or missing project file: {project_dir.name}")
            continue
        try:
            with project_file_path.open('r', encoding='utf-8') as f:
                project_data = f.read()
            project = Project.model_validate_json(project_data)
            projects.append(project)
        except Exception as e:
            LOG.error(f"Error loading project from {project_file_path}: {e}")
    return projects



@app.resource
async def open_project(project_id: str):
    """
    Open a project by its ID. This is the first thing that must be done before models are
    created or modified. When a project is opened, the current open project, if any, is closed,
    and any context pertaining to it should be disregarded.
    """
    LOG.info(f"Opening project with ID: {project_id}")
    # In a real application, you would load the project data here
    data: str = (get_path_to_project(project_id) /  PROJECT_FILE_NAME).read_text(encoding='utf-8')
    global CURRENT_OPEN_PROJECT
    CURRENT_OPEN_PROJECT = Project.model_validate_json(data)
    return CURRENT_OPEN_PROJECT


@app.resource(description="Get the current open project. This is used to get the current open project, if any. If no project is open, this will return None.")
async def get_current_open_project(project_id: str) -> Optional[Project]:
    return CURRENT_OPEN_PROJECT


LOG.info("EnrichMCP has been imported...")

# Run the server
if __name__ == "__main__":
    LOG.info("Starting EnrichMCP First API...")
    app.run()
