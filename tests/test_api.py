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
    get_entity_by_name,
    get_last_inserted_instance_id,
    add_relationship_to_entity_schema,
    Project,
    ModelField,
    EntitySchemaRelationship,
    Notice
)
from enrichmcp_first_api.model import WorldBuilderEntity


# Test utility functions

# Common setup utilities
async def setup_test_project() -> Project:
    """Create and return a standard test project."""
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    return await create_new_project(project)


def assert_entity_is_valid(entity_class, expected_name: str):
    """Validate that an entity class is properly structured."""
    assert entity_class.__name__ == expected_name
    assert issubclass(entity_class, BaseModel), f"Entity {expected_name} should be a subclass of BaseModel"
    assert issubclass(entity_class, WorldBuilderEntity), f"Entity {expected_name} should be a subclass of WorldBuilderEntity"


async def create_test_entity() -> tuple[str, list[ModelField], Type[WorldBuilderEntity]]:
    """Create a test entity and return name, fields, and class."""
    entity_name, fields = generate_random_entity()
    result = await create_world_builder_entity(entity_name, fields)
    assert result is None
    entity_class = get_entity_by_name(entity_name)
    assert entity_class is not None
    return entity_name, fields, entity_class


def validate_field_value_and_type(field: ModelField, actual_value, expected_value):
    """Validate field value and type match expectations."""
    assert actual_value == expected_value, f"Field {field.name}: expected {expected_value}, got {actual_value}"
    
    type_checks = {
        "str": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int), 
        "float": lambda v: isinstance(v, float),
        "bool": lambda v: isinstance(v, bool)
    }
    check_func = type_checks.get(field.type)
    if check_func:
        assert check_func(actual_value), f"Field {field.name} should be {field.type}"


def find_entity_in_models(entity_name: str) -> Type[WorldBuilderEntity]:
    """Find and return entity class from MODELS list."""
    from enrichmcp_first_api.api import MODELS
    for model in MODELS:
        if model.__name__ == entity_name:
            return model
    return None


def assert_relationship_fields_added(entity_class, original_field_count: int, target_entity_name: str):
    """Verify relationship fields were added with correct metadata."""
    current_fields = entity_class.model_fields
    assert len(current_fields) > original_field_count, f"Entity should have relationship fields added. Original: {original_field_count}, Current: {len(current_fields)}"
    
    # Find relationship field
    relationship_found = False
    for field_name, field in current_fields.items():
        json_extra = getattr(field, 'json_schema_extra', {}) or {}
        if json_extra.get('is_relationship', False):
            relationship_found = True
            assert json_extra.get('target_instance_type') == target_entity_name, f"Relationship should target {target_entity_name}"
    assert relationship_found, f"Entity should have at least one relationship field"


@pytest.fixture
def relationship_test_data():
    """Fixture providing two different entities for relationship testing."""
    entity1_name, entity1_fields = generate_random_entity()
    entity2_name, entity2_fields = generate_random_entity()
    
    # Ensure entities have different names
    while entity2_name == entity1_name:
        entity2_name, entity2_fields = generate_random_entity()
    
    return entity1_name, entity1_fields, entity2_name, entity2_fields


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
    created_project = await setup_test_project()
    
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
    await setup_test_project()
    
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
    await setup_test_project()
    
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
    await setup_test_project()
    
    # Create test entity
    entity_name, fields, entity_class = await create_test_entity()
    
    # Verify the entity was created and is properly typed
    entities = await list_world_builder_entities()
    assert len(entities) == 1
    created_entity = entities[0]
    assert_entity_is_valid(created_entity, entity_name)


@pytest.mark.asyncio
async def test_list_entities_empty(mock_user_data_dir):
    """Test listing entities when no entities exist."""
    # Create and open a project first
    await setup_test_project()
    
    # List entities
    entities = await list_world_builder_entities()
    
    # Should be empty
    assert entities == []


@pytest.mark.asyncio
async def test_list_entities_with_entity(mock_user_data_dir):
    """Test listing entities after creating one."""
    # Create and open a project first
    await setup_test_project()
    
    # Create test entity
    entity_name, fields, entity_class = await create_test_entity()
    
    # List entities
    entities = await list_world_builder_entities()
    
    # Verify we get one entity back
    assert len(entities) == 1
    assert_entity_is_valid(entities[0], entity_name)


@pytest.mark.asyncio
async def test_get_entity_by_name(mock_user_data_dir):
    """Test retrieving an entity by its name."""
    # Create and open a project first
    await setup_test_project()
    
    # Create test entity
    entity_name, fields, entity_class = await create_test_entity()
    
    # Get the entity by name
    retrieved_entity = get_entity_by_name(entity_name)
    
    # Verify the entity was retrieved correctly
    assert retrieved_entity is not None, f"Should be able to retrieve entity with name {entity_name}"
    assert_entity_is_valid(retrieved_entity, entity_name)
    
    # Test retrieving non-existent entity
    non_existent_entity = get_entity_by_name("NonExistentEntity")
    assert non_existent_entity is None, "Should return None for non-existent entity name"


@pytest.mark.asyncio
async def test_create_and_retrieve_instance(mock_user_data_dir):
    """Test creating an entity instance and retrieving it with field validation."""
    # Create and open a project first
    await setup_test_project()
    
    # Create test entity
    entity_name, fields, entity_class = await create_test_entity()
    
    # Generate random instance data
    instance_data = generate_random_instance(entity_name, fields)
    
    result = create_world_builder_entity_instance(entity_name, instance_data)
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
    assert retrieved_instance.__class__.__name__ == entity_name, f"Retrieved instance should be a {entity_name}"
    
    # Verify all field values and types are correct using utility function
    for field in fields:
        field_value = getattr(retrieved_instance, field.name)
        expected_value = instance_data[field.name]
        validate_field_value_and_type(field, field_value, expected_value)
    
    # Test retrieving non-existent instance
    non_existent_instance = get_instance_by_id(999)
    assert non_existent_instance is None, "Should return None for non-existent instance ID"


def test_generate_random_entity():
    """Test the random entity generator utility function."""
    # Generate two entities
    entity_name1, fields1 = generate_random_entity()
    entity_name2, fields2 = generate_random_entity()
    
    # Basic validation
    assert isinstance(entity_name1, str) and len(entity_name1) >= 5
    assert entity_name1[0].isupper() and entity_name1[1:].islower()
    assert isinstance(fields1, list) and 2 <= len(fields1) <= 6
    
    # Validate field structure
    for field in fields1:
        assert isinstance(field, ModelField)
        assert field.type in ["str", "int", "float", "bool"]
        assert len(field.name) >= 3 and field.name.islower()
        assert field.description
    
    # Entities should be different
    assert entity_name1 != entity_name2
    assert [f.name for f in fields1] != [f.name for f in fields2]
    
    # No duplicate field names within entities
    assert len(set(f.name for f in fields1)) == len(fields1)
    assert len(set(f.name for f in fields2)) == len(fields2)


def test_generate_random_instance():
    """Test the random instance generator utility function."""
    # Use generator for test fields
    _, test_fields = generate_random_entity()
    
    # Generate and validate instances  
    instance1 = generate_random_instance("TestEntity", test_fields)
    instance2 = generate_random_instance("TestEntity", test_fields)
    
    # Basic validation
    assert isinstance(instance1, dict) and len(instance1) == len(test_fields)
    assert isinstance(instance2, dict) and len(instance2) == len(test_fields)
    assert instance1 != instance2  # Should be different
    
    # Validate field types and values
    for field in test_fields:
        assert field.name in instance1
        value = instance1[field.name]
        if field.type == "str":
            assert isinstance(value, str) and len(value) >= 5
        elif field.type == "int":
            assert isinstance(value, int) and -100 <= value <= 1000
        elif field.type == "float":
            assert isinstance(value, float) and -100.0 <= value <= 1000.0
        elif field.type == "bool":
            assert isinstance(value, bool)
    
    # Test edge cases
    assert generate_random_instance("Empty", []) == {}
    unknown_field = [ModelField(name="test", type="unknown", description="Test")]
    unknown_instance = generate_random_instance("Unknown", unknown_field)
    assert unknown_instance["test"] == "default_test"


@pytest.mark.parametrize("cardinality", [
    "one_to_one", "one_to_many", "many_to_one", "many_to_many"
])
@pytest.mark.asyncio
async def test_entity_relationship_cardinality(mock_user_data_dir, relationship_test_data, cardinality):
    """Test creating relationships between entities with different cardinalities."""
    # Setup project
    await setup_test_project()
    
    # Unpack test data
    entity1_name, entity1_fields, entity2_name, entity2_fields = relationship_test_data
    
    # Create both entities
    result1 = await create_world_builder_entity(entity1_name, entity1_fields)
    result2 = await create_world_builder_entity(entity2_name, entity2_fields)
    assert result1 is None and result2 is None
    
    # Create schema relationship
    relationship = EntitySchemaRelationship(
        world_builder_entity_name_one=entity1_name,
        world_builder_entity_name_two=entity2_name,
        cardinality=cardinality
    )
    
    # Add relationship to schema
    result = add_relationship_to_entity_schema(relationship)
    
    # Verify relationship was added successfully
    assert isinstance(result, Notice), f"Expected Notice, got {type(result)}"
    assert "added successfully" in result.message, f"Expected success message, got: {result.message}"
    
    # Find the updated entity classes using utility function
    entity1_class = find_entity_in_models(entity1_name)
    entity2_class = find_entity_in_models(entity2_name)
    
    assert entity1_class is not None, f"Entity {entity1_name} should exist in MODELS after relationship creation"
    assert entity2_class is not None, f"Entity {entity2_name} should exist in MODELS after relationship creation"
    
    # Verify relationship fields were added using utility function
    assert_relationship_fields_added(entity1_class, len(entity1_fields), entity2_name)
    assert_relationship_fields_added(entity2_class, len(entity2_fields), entity1_name)