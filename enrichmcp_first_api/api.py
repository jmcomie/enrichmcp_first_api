from __future__ import annotations
from datetime import date
import json
import os
from typing import Literal, Optional
from altair import Type
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import BaseModel, Field
from functools import cache
import base64
from io import BytesIO
from appdirs import user_data_dir
from pathlib import Path
import logging
from typing import ForwardRef
import enrichmcp_first_api
from enrichmcp_first_api.lib.logger import FileLogger
import importlib
import sys
import importlib.util

from enrichmcp_first_api.model import WorldBuilderEntity
# Create the application
app = EnrichMCP(title="WorldBuilder", description="A simple API for world building and creating new character classes, buildings, towns, and relationships. A project must always be opened before any models are created or modified.")
MODELS_DIRECTORY: Path = Path(f"{enrichmcp_first_api.__path__[0]}/models")
PROJECT_FILE_NAME: str = "project.json"

FORWARD_REF_SEMAPHORE: str = "FORWARD_REF:"

MODELS: list[Type[EnrichModel]] = []
INSTANCES_FILENAME: str = "instances.json"
CLASSNAME_FIELD_NAME: str = "__class_name__"
LAST_INSERTED_INSTANCE_ID: Optional[int] = None
LAST_UPDATED_INSTANCE_ID: Optional[int] = None

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


class RelationshipField(BaseModel):
    name: str
    target: str
    side_cardinality: SideCardinality
    description: str


# RelationshipCardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


def model_string_from_fields(name: str, model_fields: list[ModelField], relationships: list[RelationshipField] = []) -> str:
    """
    Add a model to the EnrichMCP application.
    This is used to register models that can be used in the current project.
    """
    # iterate over the fields and create a string representation of the model
    model_str: str = f"""\
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import Field
from enrichmcp_first_api.model import WorldBuilderEntity

class {name}(WorldBuilderEntity):
    \"\"\"A pydantic model named {name} with fields: {', '.join([field.name for field in model_fields])}.\"\"\"
"""
    for field in model_fields:
        model_str += f"    {field.name}: {field.type} = Field(description=\"{field.description}\")\n"
    for relation_field in relationships:
        type_str = 'list[int]' if relation_field.side_cardinality == "many" else 'int'
        model_str += f"    {relation_field.name}: {type_str} = Field(default=None, description=\"{relation_field.description}\")\n"
    model_str += "\n"
    return model_str


def import_module_from_path(module_name, module_path, force_reload=False):
    """Imports a module from a given file path and applies entity decorators to all classes."""
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Module file not found: {module_path}")
    
    # Simple force reload - just remove from sys.modules
    if force_reload and module_name in sys.modules:
        del sys.modules[module_name]
        # Optionally clear MODELS list if you want to start fresh
        MODELS.clear()  # Add this line if you want to clear all models
    
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
            MODELS.append(decorated_class)
    return module

def write_model_to_file_and_import(model_name: str, model_fields: list[ModelField], relationships: list[RelationshipField] = [], force_reload= False) -> None:
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
    model_str: str = model_string_from_fields(model_name, model_fields, relationships)
    with open(model_path, 'w', encoding='utf-8') as f:
        f.write(model_str)
    LOG.info(f"Model {model_name} written to {model_path}")
    try:
        importlib.invalidate_caches()  # Clear the import cache
        # import model_path
        import_module_from_path(model_name, model_path, force_reload=force_reload)
    except Exception as e:
        LOG.error(f"Error importing model {model_name} from {model_path}: {e}")
        raise ImportError(f"Error importing model {model_name} from {model_path}: {e}")


@app.resource(description="This is an optional error response. If an error occurs, attempt correct and call tool again")
class ErrorResponse(EnrichModel):
    error: str = Field(description="A description of the error that occurred.")


@app.resource(description="Create a new pydantic model based on the current open project theme. Never call unless expressly directed by the user.")
async def create_world_builder_entity(name: str, fields: list[ModelField]) -> Optional[ErrorResponse]:
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
async def list_world_builder_entities() -> list[Type[EnrichModel]]:
    if not MODELS:
        project_path: Path = Path(get_path_to_project(CURRENT_OPEN_PROJECT.id))
        model_path: Path = project_path / "models"
        for model_file in model_path.glob("*.py"):
            if model_file.name.startswith("__") or model_file.name == "base.py":
                continue
            try:
                import_module_from_path(model_file.stem, model_file)
            except Exception as e:
                LOG.error(f"Error loading model {model_file}: {e}")
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
    global LAST_INSERTED_INSTANCE_ID
    LAST_INSERTED_INSTANCE_ID = None
    global LAST_UPDATED_INSTANCE_ID
    LAST_UPDATED_INSTANCE_ID = None
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


###############
# START PASTE #
###############

@cache
def get_world_builder_entity_class_by_name(classname: str) ->Type[WorldBuilderEntity]:
    for enrichmcp_class in MODELS:
        if enrichmcp_class.__name__ == classname:
            return enrichmcp_class


def get_enrichmcp_class(data_dict: dict) -> Type[EnrichMCP]:
     return get_world_builder_entity_class_by_name(data_dict.get(CLASSNAME_FIELD_NAME))


@app.entity(description="A container for an instance of a world builder entity and its identifier.")
class InstanceWithId(EnrichModel):
    id: int = Field(description="The unique identifier for the instance of the world builder entity.")
    instance: WorldBuilderEntity = Field(description="The instance of the world builder entity. This is a pydantic model that represents the data for the instance.")


def get_instances_filepath() -> Path:
    if not CURRENT_OPEN_PROJECT:
        raise ValueError("No project is currently open. Please open a project before accessing instances.")
    instances_filepath: Path = get_path_to_project(CURRENT_OPEN_PROJECT.id) / INSTANCES_FILENAME
    if not instances_filepath.exists():
        # Create the file with an empty list if it doesn't exist
        instances_filepath.write_text(json.dumps([]), 'utf-8')
    return instances_filepath


@app.resource(description="Update the provided model instance by replacing the instance with the id with the given instance.")
def update_world_builder_entity_instance(id: int, instance: WorldBuilderEntity):
    instance_dicts: list[dict] =  json.loads(get_instances_filepath().read_text('utf-8'))
    try:
        instance_dicts[id] = instance.model_dump()
        instance_dicts[id][CLASSNAME_FIELD_NAME] = instance.__class__.__name__
        global LAST_UPDATED_INSTANCE_ID
        LAST_UPDATED_INSTANCE_ID = id
        get_instances_filepath().write_text(json.dumps(instance_dicts), 'utf-8')
    except KeyError:
        return None


@app.resource(description="Fetch the instance of a world builder entity by its ID.")
def get_instance_by_id(id: int) -> Optional[WorldBuilderEntity]:
    instance_dicts: list[dict] =  json.loads(get_instances_filepath().read_text('utf-8'))
    LOG.info(f"Found {len(instance_dicts)} instances in the file.")
    try:
        classname: str = instance_dicts[id].pop(CLASSNAME_FIELD_NAME)
        cls: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(classname)
        if cls is None:
            LOG.warning(f"Could not find class {classname} for instance with ID {id}.")
            return None
        return cls.model_validate(instance_dicts[id])
    except KeyError as e:
        LOG.exception(f"Error retrieving instance with ID {id}: {e}")
        LOG.warning("Returning None as the instance could not be found.")
        return None
    except Exception as e:
        LOG.exception(f"Unexpected error retrieving instance with ID {id}: {e}")
        return None


@app.resource(description="Get a list of all instances of a world builder entity type.")
def list_entity_instances(world_builder_entity_name: str) -> list[InstanceWithId]:
    """world_builder_entity_name is the exact class name of the correct pydantic model"""
    model_instances: list[InstanceWithId] = []
    instance_dicts: list[dict] =  json.loads(get_instances_filepath().read_text('utf-8'))
    for index, instance_dict in enumerate(instance_dicts):
         classname: Optional[str] = instance_dict.pop(CLASSNAME_FIELD_NAME)
         if classname != world_builder_entity_name:
             LOG.warning(f"Instance with ID {index} has class name {classname}, which does not match the requested entity name {world_builder_entity_name}. Skipping.")
             continue
         cls: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(classname)
         if cls is None:
             LOG.warning(f"Could not find class {classname} for instance with ID {index}. Skipping.")
             continue

         model_instances.append(InstanceWithId(id=index, instance=cls.model_validate(instance_dict)))
    return model_instances


def list_world_builder_entity_class_names() -> list[str]:
    """List model names when attempting to identify a model
    by a user-given description."""
    class_names: list[str] = []
    for enrichmcp_class in MODELS:
        class_names.append(enrichmcp_class.__name__)
    return class_names



RelationshipCardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]
SideCardinality = Literal["one", "many"]


@app.entity(description="A notice for the LLM to consider a directive, such as when some follow up action should be taken or considered.")
class Notice(EnrichModel):
    message: str = Field(description="A message for the LLM directing it to consider something.")


@app.resource(description="Get the last inserted instance ID. This is used to retrieve the ID of the last instance that was inserted.")
def get_last_inserted_instance_id() -> Optional[int]:
    return LAST_INSERTED_INSTANCE_ID

@app.resource(description="Get the last updated instance ID. This is used to retrieve the ID of the last instance that was updated.")
def get_last_updated_instance_id() -> Optional[int]:
    return LAST_UPDATED_INSTANCE_ID

# def add_model_type should take create_relationship: Optional[Relationship] 
# instances will love in one file so that their

# model instances should be listed with ids for retrieval
# 
# create the instance and if there are undefined relationships remind it
# "Notice:"" to review prompt for those relationships


@app.entity(description="A relationship between two world builder entities. This is used to define the relationship schema.")
class EntitySchemaRelationship(EnrichModel):
    world_builder_entity_name_one: str = Field(description="Name of WorldBuildEntity, representing the first cardinality operand. i.e. the 'one' in a one-to-many relationship or the 'many' in a many-to-one relationship.")
    world_builder_entity_name_two: str = Field(description="Name of WorldBuildEntity, representing the second cardinality operand. i.e. the 'many' in a one-to-many relationship or the 'one' in a many-to-one relationship.")
    cardinality: RelationshipCardinality =  Field(description="The cardinality of the relationship. Supported values are 'one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'.")

@app.entity(description="A relationship between two instances of world builder entities.")
class InstanceRelationship(EnrichModel):
    instance_id_one: int = Field(description="The ID of the first instance in the relationship.")
    instance_id_two: int = Field(description="The ID of the second instance in the relationship.")


def get_model_fields_and_relationships_from_entity(entity: Type[WorldBuilderEntity]) -> tuple[list[ModelField], list[RelationshipField]]:
    """
    Get the model fields and relationships from a world builder entity class.
    This is used to extract the fields and relationships defined in the entity class.
    """
    model_fields: list[ModelField] = []
    relationships: list[RelationshipField] = []
    
    for field_name, field in entity.model_fields.items():
        if FORWARD_REF_SEMAPHORE in field.description:
            # Handle relationship fields
            side_cardinality: SideCardinality = "many" if field.type == list else "one"
            relationships.append(RelationshipField(
                name=entity.__name__,
                target=field_name,
                side_cardinality=side_cardinality,
                description=field.description
            ))
        else:
            # Handle regular fields
            model_fields.append(ModelField(
                name=field_name,
                type=field.annotation.__name__,
                description=field.description
            ))
    
    return model_fields, relationships


def _add_relationship_to_entity_schema(relationship: EntitySchemaRelationship) -> Optional[Notice]:
    """
    Add a relationship to the entity schema. This is used to define the relationship schema between two world builder entities.
    """
    LOG.info(f"Adding relationship to entity schema: {relationship.world_builder_entity_name_one} and {relationship.world_builder_entity_name_two} with cardinality {relationship.cardinality}")
    entity_type_one: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(relationship.world_builder_entity_name_one)
    entity_type_two: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(relationship.world_builder_entity_name_two)
    if entity_type_one is None or entity_type_two is None:
        return Notice(message=f"Error: One or both of the specified world builder entities do not exist: {relationship.world_builder_entity_name_one}, {relationship.world_builder_entity_name_two}. Please ensure they are created before adding a relationship.")
    for entity_type in [entity_type_one, entity_type_two]:
        model_fields, relationships = get_model_fields_and_relationships_from_entity(entity_type)
        # Check if the relationship already exists
        # Add the relationship to the entity schema
        target =  relationship.world_builder_entity_name_two if entity_type.__name__ == relationship.world_builder_entity_name_one else relationship.world_builder_entity_name_one
        if any(rel.name == relationship.world_builder_entity_name_two and rel.target == target for rel in relationships):
            LOG.warning(f"Relationship {relationship.world_builder_entity_name_one} to {relationship.world_builder_entity_name_two} already exists in {entity_type.__name__}. Skipping.")
            continue
        side_cardinality: str
        if relationship.world_builder_entity_name_one == entity_type.__name__:
            # Entity is on the "one" side of the relationship definition
            if relationship.cardinality in ["one_to_many", "one_to_one"]:
                side_cardinality = "one"
            else:  # many_to_one, many_to_many
                side_cardinality = "many"
        elif relationship.world_builder_entity_name_two == entity_type.__name__:
            # Entity is on the "two" side of the relationship definition
            if relationship.cardinality in ["many_to_one", "one_to_one"]:
                side_cardinality = "one"
            else:  # one_to_many, many_to_many
                side_cardinality = "many"
        else:
            # Entity is not part of this relationship - this shouldn't happen
            # but handle gracefully
            return  Notice(message=f"Error: Entity {entity_type.__name__} is not part of the relationship {relationship.world_builder_entity_name_one} to {relationship.world_builder_entity_name_two}. Please ensure the relationship is defined correctly.")
        relationships.append(RelationshipField(
            name=relationship.world_builder_entity_name_two if entity_type.__name__ == relationship.world_builder_entity_name_one else relationship.world_builder_entity_name_one,
            target=target,
            side_cardinality=side_cardinality,
            description=f"A relationship to {side_cardinality} {target} instance(s). {FORWARD_REF_SEMAPHORE}:{target}"
        ))
        for model in MODELS:
            if model.__name__ == entity_type.__name__:
                # Update the model in the MODELS list
                MODELS.remove(model)
                break
        # Write the updated model to file
        write_model_to_file_and_import(entity_type.__name__, model_fields, relationships, force_reload=True)


@app.resource(description="Add a relationship to the entity schema. This is used to define the relationship schema between two world builder entities.")
def add_relationship_to_entity_schema(relationship: EntitySchemaRelationship) -> Optional[Notice]:
    LOG.info(f"Adding relationship to entity schema: {relationship.world_builder_entity_name_one} and {relationship.world_builder_entity_name_two} with cardinality {relationship.cardinality}")
    entity_type_one: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(relationship.world_builder_entity_name_one)
    entity_type_two: Type[WorldBuilderEntity] = get_world_builder_entity_class_by_name(relationship.world_builder_entity_name_two)
    if entity_type_one is None or entity_type_two is None:
        return Notice(message=f"Error: One or both of the specified world builder entities do not exist: {relationship.world_builder_entity_name_one}, {relationship.world_builder_entity_name_two}. Please ensure they are created before adding a relationship.")
    try:
        _add_relationship_to_entity_schema(relationship)
    except Exception as e:
        LOG.exception(f"Error adding relationship to entity schema: {e}")
        return Notice(message=f"Error adding relationship to entity schema: {e}. Please ensure the relationship is defined correctly.")
    return Notice(message=f"Relationship {relationship.world_builder_entity_name_one} to {relationship.world_builder_entity_name_two} with cardinality {relationship.cardinality} added successfully.")


@app.resource(description="Add a relationship between two world builder entities per their cardinality. e.g. if the relationship is one-to-many, then the first instance will have a list of second instances.")
def add_relationship_between_instances(instance_relationship: InstanceRelationship) -> Optional[Notice]:
    LOG.info(f"Adding relationship between instances: {instance_relationship.instance_id_one} and {instance_relationship.instance_id_two}")
    try:
        instance_one: WorldBuilderEntity = get_instance_by_id(instance_relationship.instance_id_one)
        instance_two: WorldBuilderEntity = get_instance_by_id(instance_relationship.instance_id_two)
        if instance_one is None or instance_two is None:
            LOG.error(f"One or both instances do not exist: {instance_relationship.instance_id_one}, {instance_relationship.instance_id_two}.")
            return Notice(message=f"Error: One or both instances do not exist: {instance_relationship.instance_id_one}, {instance_relationship.instance_id_two}. Please ensure they are created before adding a relationship.")
        LOG.info(f"model fields: {instance_one.__class__.model_fields}")
        if isinstance(instance_one.__class__.model_fields[instance_two.__class__.__name__], list):
            # If the field is a list, append the second instance to the first instance's field
            instance_one.__class__.model_fields[instance_two.__class__.__name__].append(instance_relationship.instance_id_two)
        else:
            instance_one.__class__.model_fields[instance_two.__class__.__name__] = instance_relationship.instance_id_two
        
        if isinstance(instance_two.__class__.model_fields[instance_one.__class__.__name__], list):
            # If the field is a list, append the first instance to the second instance's field
            instance_two.__class__.model_fields[instance_one.__class__.__name__].append(instance_relationship.instance_id_one)
        else:
            instance_two.__class__.model_fields[instance_one.__class__.__name__] = instance_relationship.instance_id_one
    except Exception as e:
        LOG.exception(f"Error adding relationship between instances: {e}")
        return Notice(message=f"Error adding relationship between instances: {e}. Please ensure the instances are created and the relationship is defined correctly.")


def has_empty_relationship(instance: WorldBuilderEntity):
    # Returns if an instance has a relationship field
    # with no value.
    for field_name, field in instance.__class__.model_fields.items():
        if FORWARD_REF_SEMAPHORE in field.description:
            if not getattr(instance, field_name) and getattr(instance, field_name) != 0:
                LOG.info(f"Instance {instance.__class__.__name__} has empty relationship field: {field_name}")
                return True
    LOG.info(f"Instance {instance.__class__.__name__} has no empty relationship fields.")
    return False


@app.resource(description="Create a new instance of a world builder entity. This is an dict containing data of one of the subclasses of WorldBuilderEntity, created with a call to create_world_builder_entity.")
def create_world_builder_entity_instance(world_builder_entity_name: str, data_dict: dict) -> Optional[Notice]:
    LOG.info(f"Creating instance of {data_dict}. Type: {type(data_dict)}")
    LOG.info(f"Instance class name: {data_dict.__class__.__name__}")
    LOG.info(f"Data for instance: {data_dict}")
    LOG.info(f"World builder entity name: {world_builder_entity_name}")
    if not data_dict:
        LOG.warning("Instance data is empty.")
        return Notice(message="Instance data is empty. Please provide valid data for the instance corresponding to the schema of the entity name.")
    try:
        instance = get_world_builder_entity_class_by_name(world_builder_entity_name).model_validate(data_dict)
    except Exception as e:
        LOG.error(f"Error validating instance data: {e}")
        return Notice(message=f"Error validating instance data: {e}. Please provide valid data for the instance corresponding to the schema of the entity name.")
    try:
        instance_dicts: list[dict] =  json.loads(get_instances_filepath().read_text('utf-8'))
        #return Notice(message="Success! Instance created.")
        model_dict: dict = instance.model_dump()
        model_dict[CLASSNAME_FIELD_NAME] = instance.__class__.__name__
        instance_dicts.append(model_dict)
        global LAST_INSERTED_INSTANCE_ID
        LAST_INSERTED_INSTANCE_ID = len(instance_dicts) - 1
        get_instances_filepath().write_text(json.dumps(instance_dicts), 'utf-8')
    except Exception as e:
        LOG.exception(f"Error writing instance data: {e}")
        return Notice(message=f"Error writing instance data: {e}. Please try again.")
    if has_empty_relationship(instance):
        return Notice(message="Success! Instance created. Now review prompt and add relationship data between two instances if applicable.")


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
    global LAST_INSERTED_INSTANCE_ID
    LAST_INSERTED_INSTANCE_ID = None
    global LAST_UPDATED_INSTANCE_ID
    LAST_UPDATED_INSTANCE_ID = None
    return CURRENT_OPEN_PROJECT


@app.resource(description="Get the current open project. This is used to get the current open project, if any. If no project is open, this will return None.")
async def get_current_open_project(project_id: str) -> Optional[Project]:
    return CURRENT_OPEN_PROJECT


LOG.info("EnrichMCP has been imported...")

# Run the server
if __name__ == "__main__":
    LOG.info("Starting EnrichMCP First API...")
    app.run()
