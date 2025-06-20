import pytest
import asyncio
import random
import string
from typing import Type
from pydantic import BaseModel
from enrichmcp_first_api.api import (
    get_app_dir,
    create_new_project,
    list_projects,
    open_project,
    create_world_builder_entity,
    list_world_builder_entities,
    create_world_builder_entity_instance,
    get_instance_by_id,
    get_last_inserted_instance_id,
    Project,
    ModelField
)
from enrichmcp_first_api.model import WorldBuilderEntity


# Test utility functions
def generate_random_entity() -> tuple[str, list[ModelField]]:
    """
    Generate a random entity with random name and fields.
    Returns tuple of (entity_name, list_of_fields).
    """
    # Generate random entity name
    entity_name = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
                  ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 12)))
    
    # Generate random number of fields (2-6)
    num_fields = random.randint(2, 6)
    fields = []
    
    # Available field types with their generators
    field_types = ["str", "int", "float", "bool"]
    
    for i in range(num_fields):
        # Generate random field name
        field_name = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
        
        # Choose random type
        field_type = random.choice(field_types)
        
        # Generate description
        description = f"A {field_type} field for {field_name}"
        
        fields.append(ModelField(
            name=field_name,
            type=field_type,
            description=description
        ))
    
    return entity_name, fields


def generate_random_instance(entity_name: str, fields: list[ModelField]) -> dict:
    """
    Generate a random instance data dictionary for a given entity.
    Takes entity name and field list, returns dict with random values.
    """
    instance_data = {}
    
    for field in fields:
        if field.type == "str":
            # Generate random string (5-15 characters)
            value = ''.join(random.choices(string.ascii_letters + string.digits + ' ', 
                                         k=random.randint(5, 15))).strip()
        elif field.type == "int":
            # Generate random integer (-100 to 1000)
            value = random.randint(-100, 1000)
        elif field.type == "float":
            # Generate random float (-100.0 to 1000.0)
            value = round(random.uniform(-100.0, 1000.0), 2)
        elif field.type == "bool":
            # Generate random boolean
            value = random.choice([True, False])
        else:
            # Default to string for unknown types
            value = f"default_{field.name}"
        
        instance_data[field.name] = value
    
    return instance_data


def test_mocked_user_data_dir_contains_tmp(mock_user_data_dir):
    """Test that the mocked user_data_dir fixture returns a temporary directory."""
    # Get the app directory (which should be mocked)
    app_dir = get_app_dir()
    
    # Verify that the returned directory path contains 'tmp'
    assert "tmp" in app_dir.lower(), f"Expected 'tmp' in app directory path, got: {app_dir}"
    
    # Also verify that it matches our fixture value
    assert app_dir == mock_user_data_dir, f"App dir {app_dir} should match fixture {mock_user_data_dir}"


@pytest.mark.asyncio
async def test_create_project(mock_user_data_dir):
    """Test creating a new project."""
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    
    # Create the project
    created_project = await create_new_project(project)
    
    # Verify the project was created
    assert created_project.id == "test_project"
    assert created_project.name == "Test Project"
    assert created_project.theme == "fantasy"


def test_list_projects_empty(mock_user_data_dir):
    """Test listing projects when no projects exist."""
    projects = list_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_list_projects_with_project(mock_user_data_dir):
    """Test listing projects after creating one."""
    # Create a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # List projects
    projects = list_projects()
    
    # Verify we get one project back
    assert len(projects) == 1
    assert projects[0].id == "test_project"
    assert projects[0].name == "Test Project"


@pytest.mark.asyncio
async def test_open_project(mock_user_data_dir):
    """Test opening an existing project."""
    # Create a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Open the project
    opened_project = await open_project("test_project")
    
    # Verify the project was opened
    assert opened_project.id == "test_project"
    assert opened_project.name == "Test Project"
    assert opened_project.theme == "fantasy"


@pytest.mark.asyncio
async def test_create_entity(mock_user_data_dir):
    """Test creating a new world builder entity."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Create entity fields
    fields = [
        ModelField(name="name", type="str", description="The character's name"),
        ModelField(name="level", type="int", description="The character's level"),
        ModelField(name="health", type="float", description="The character's health points")
    ]
    
    # Create the entity
    result = await create_world_builder_entity("Character", fields)
    
    # Verify no error was returned
    assert result is None
    
    # Verify the entity was created and is properly typed
    entities = await list_world_builder_entities()
    assert len(entities) == 1
    created_entity = entities[0]
    assert created_entity.__name__ == "Character"
    assert issubclass(created_entity, BaseModel), f"Created entity {created_entity.__name__} should be a subclass of BaseModel"
    assert issubclass(created_entity, WorldBuilderEntity), f"Created entity {created_entity.__name__} should be a subclass of WorldBuilderEntity"


@pytest.mark.asyncio
async def test_list_entities_empty(mock_user_data_dir):
    """Test listing entities when no entities exist."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # List entities
    entities = await list_world_builder_entities()
    
    # Should be empty
    assert entities == []


@pytest.mark.asyncio
async def test_list_entities_with_entity(mock_user_data_dir):
    """Test listing entities after creating one."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Create entity fields
    fields = [
        ModelField(name="name", type="str", description="The character's name"),
        ModelField(name="level", type="int", description="The character's level")
    ]
    
    # Create the entity
    await create_world_builder_entity("Character", fields)
    
    # List entities
    entities = await list_world_builder_entities()
    
    # Verify we get one entity back
    assert len(entities) == 1
    assert entities[0].__name__ == "Character"
    
    # Verify it's properly typed as a BaseModel and WorldBuilderEntity subclass
    assert issubclass(entities[0], BaseModel), f"Entity {entities[0].__name__} should be a subclass of BaseModel"
    assert issubclass(entities[0], WorldBuilderEntity), f"Entity {entities[0].__name__} should be a subclass of WorldBuilderEntity"


@pytest.mark.asyncio
async def test_create_and_retrieve_instance(mock_user_data_dir):
    """Test creating an entity instance and retrieving it with field validation."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Create an entity first
    fields = [
        ModelField(name="name", type="str", description="The character's name"),
        ModelField(name="level", type="int", description="The character's level"),
        ModelField(name="health", type="float", description="The character's health points"),
        ModelField(name="is_active", type="bool", description="Whether the character is active")
    ]
    result = await create_world_builder_entity("Character", fields)
    assert result is None
    
    # Create an instance of the entity
    instance_data = {
        "name": "Aragorn",
        "level": 42,
        "health": 100.5,
        "is_active": True
    }
    
    result = create_world_builder_entity_instance("Character", instance_data)
    # Should return None (success) or a Notice
    assert result is None or (hasattr(result, 'message') and 'Success' in result.message)
    
    # Get the ID of the created instance
    instance_id = get_last_inserted_instance_id()
    assert instance_id is not None, "Should have an instance ID after creation"
    assert isinstance(instance_id, int), "Instance ID should be an integer"
    
    # Retrieve the instance by ID
    retrieved_instance = get_instance_by_id(instance_id)
    assert retrieved_instance is not None, f"Should be able to retrieve instance with ID {instance_id}"
    
    # Verify the instance is of the correct type
    assert isinstance(retrieved_instance, WorldBuilderEntity), "Retrieved instance should be a WorldBuilderEntity"
    assert retrieved_instance.__class__.__name__ == "Character", "Retrieved instance should be a Character"
    
    # Verify all field values are correct
    assert retrieved_instance.name == "Aragorn", f"Expected name 'Aragorn', got {retrieved_instance.name}"
    assert retrieved_instance.level == 42, f"Expected level 42, got {retrieved_instance.level}"
    assert retrieved_instance.health == 100.5, f"Expected health 100.5, got {retrieved_instance.health}"
    assert retrieved_instance.is_active == True, f"Expected is_active True, got {retrieved_instance.is_active}"
    
    # Verify field types are correct
    assert isinstance(retrieved_instance.name, str), "Name should be a string"
    assert isinstance(retrieved_instance.level, int), "Level should be an integer"
    assert isinstance(retrieved_instance.health, float), "Health should be a float"
    assert isinstance(retrieved_instance.is_active, bool), "is_active should be a boolean"
    
    # Test retrieving non-existent instance
    non_existent_instance = get_instance_by_id(999)
    assert non_existent_instance is None, "Should return None for non-existent instance ID"


def test_generate_random_entity():
    """Test the random entity generator utility function."""
    # Generate first entity
    entity_name1, fields1 = generate_random_entity()
    
    # Basic validation of first entity
    assert isinstance(entity_name1, str), "Entity name should be a string"
    assert len(entity_name1) >= 5, f"Entity name should be at least 5 characters, got {len(entity_name1)}"
    assert entity_name1[0].isupper(), "Entity name should start with uppercase"
    assert entity_name1[1:].islower(), "Entity name should have lowercase after first character"
    
    assert isinstance(fields1, list), "Fields should be a list"
    assert 2 <= len(fields1) <= 6, f"Should have 2-6 fields, got {len(fields1)}"
    
    # Validate field structure
    for field in fields1:
        assert isinstance(field, ModelField), "Each field should be a ModelField"
        assert field.type in ["str", "int", "float", "bool"], f"Field type {field.type} should be supported"
        assert len(field.name) >= 3, f"Field name should be at least 3 characters, got {field.name}"
        assert field.name.islower(), f"Field name should be lowercase, got {field.name}"
        assert field.description, "Field should have a description"
    
    # Generate second entity
    entity_name2, fields2 = generate_random_entity()
    
    # Entities should be different (very high probability)
    assert entity_name1 != entity_name2, "Two generated entities should have different names"
    
    # Field names should be different (very high probability)
    field_names1 = [f.name for f in fields1]
    field_names2 = [f.name for f in fields2]
    assert field_names1 != field_names2, "Two generated entities should have different field names"
    
    # Verify no duplicate field names within single entity
    assert len(set(field_names1)) == len(field_names1), "Entity should not have duplicate field names"
    assert len(set(field_names2)) == len(field_names2), "Entity should not have duplicate field names"


def test_generate_random_instance():
    """Test the random instance generator utility function."""
    # Create a test entity with known fields
    test_fields = [
        ModelField(name="name", type="str", description="A string field"),
        ModelField(name="age", type="int", description="An integer field"),
        ModelField(name="score", type="float", description="A float field"),
        ModelField(name="active", type="bool", description="A boolean field")
    ]
    
    # Generate first instance
    instance1 = generate_random_instance("TestEntity", test_fields)
    
    # Basic validation
    assert isinstance(instance1, dict), "Instance should be a dictionary"
    assert len(instance1) == 4, "Instance should have 4 fields"
    
    # Validate field presence and types
    assert "name" in instance1, "Instance should have 'name' field"
    assert "age" in instance1, "Instance should have 'age' field"
    assert "score" in instance1, "Instance should have 'score' field"
    assert "active" in instance1, "Instance should have 'active' field"
    
    assert isinstance(instance1["name"], str), "Name should be string"
    assert isinstance(instance1["age"], int), "Age should be integer"
    assert isinstance(instance1["score"], float), "Score should be float"
    assert isinstance(instance1["active"], bool), "Active should be boolean"
    
    # Validate value ranges
    assert len(instance1["name"]) >= 5, "Name should be at least 5 characters"
    assert -100 <= instance1["age"] <= 1000, "Age should be in valid range"
    assert -100.0 <= instance1["score"] <= 1000.0, "Score should be in valid range"
    assert instance1["active"] in [True, False], "Active should be boolean"
    
    # Generate second instance
    instance2 = generate_random_instance("TestEntity", test_fields)
    
    # Instances should be different (very high probability)
    assert instance1 != instance2, "Two generated instances should be different"
    
    # Test with empty fields
    empty_instance = generate_random_instance("EmptyEntity", [])
    assert empty_instance == {}, "Instance with no fields should be empty dict"
    
    # Test with unknown field type
    unknown_field = [ModelField(name="unknown", type="unknown_type", description="Unknown type")]
    unknown_instance = generate_random_instance("UnknownEntity", unknown_field)
    assert "unknown" in unknown_instance, "Should handle unknown field types"
    assert unknown_instance["unknown"] == "default_unknown", "Unknown type should get default value"