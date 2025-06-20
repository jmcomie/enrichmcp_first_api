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
    
    # Generate random entity
    entity_name, fields = generate_random_entity()
    
    # Create the entity
    result = await create_world_builder_entity(entity_name, fields)
    
    # Verify no error was returned
    assert result is None
    
    # Verify the entity was created and is properly typed
    entities = await list_world_builder_entities()
    assert len(entities) == 1
    created_entity = entities[0]
    assert created_entity.__name__ == entity_name
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
    
    # Generate and create random entity
    entity_name, fields = generate_random_entity()
    await create_world_builder_entity(entity_name, fields)
    
    # List entities
    entities = await list_world_builder_entities()
    
    # Verify we get one entity back
    assert len(entities) == 1
    assert entities[0].__name__ == entity_name
    
    # Verify it's properly typed as a BaseModel and WorldBuilderEntity subclass
    assert issubclass(entities[0], BaseModel), f"Entity {entities[0].__name__} should be a subclass of BaseModel"
    assert issubclass(entities[0], WorldBuilderEntity), f"Entity {entities[0].__name__} should be a subclass of WorldBuilderEntity"


@pytest.mark.asyncio
async def test_get_entity_by_name(mock_user_data_dir):
    """Test retrieving an entity by its name."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Generate and create random entity
    entity_name, fields = generate_random_entity()
    await create_world_builder_entity(entity_name, fields)
    
    # Get the entity by name
    retrieved_entity = get_entity_by_name(entity_name)
    
    # Verify the entity was retrieved correctly
    assert retrieved_entity is not None, f"Should be able to retrieve entity with name {entity_name}"
    assert retrieved_entity.__name__ == entity_name, f"Retrieved entity should have name {entity_name}"
    assert issubclass(retrieved_entity, BaseModel), f"Retrieved entity should be a subclass of BaseModel"
    assert issubclass(retrieved_entity, WorldBuilderEntity), f"Retrieved entity should be a subclass of WorldBuilderEntity"
    
    # Test retrieving non-existent entity
    non_existent_entity = get_entity_by_name("NonExistentEntity")
    assert non_existent_entity is None, "Should return None for non-existent entity name"


@pytest.mark.asyncio
async def test_create_and_retrieve_instance(mock_user_data_dir):
    """Test creating an entity instance and retrieving it with field validation."""
    # Create and open a project first
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
    # Generate random entity and create it
    entity_name, fields = generate_random_entity()
    result = await create_world_builder_entity(entity_name, fields)
    assert result is None
    
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
    
    # Verify all field values and types are correct
    for field in fields:
        field_value = getattr(retrieved_instance, field.name)
        expected_value = instance_data[field.name]
        assert field_value == expected_value, f"Field {field.name}: expected {expected_value}, got {field_value}"
        
        # Verify field types
        if field.type == "str":
            assert isinstance(field_value, str), f"Field {field.name} should be string"
        elif field.type == "int":
            assert isinstance(field_value, int), f"Field {field.name} should be integer"
        elif field.type == "float":
            assert isinstance(field_value, float), f"Field {field.name} should be float"
        elif field.type == "bool":
            assert isinstance(field_value, bool), f"Field {field.name} should be boolean"
    
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
    project = Project(id="test_project", name="Test Project", theme="fantasy")
    await create_new_project(project)
    
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
    
    # Verify entities were updated by getting fresh entities from the updated MODELS list
    from enrichmcp_first_api.api import MODELS
    
    # Find the updated entity classes in MODELS
    entity1_class = None
    entity2_class = None
    for model in MODELS:
        if model.__name__ == entity1_name:
            entity1_class = model
        elif model.__name__ == entity2_name:
            entity2_class = model
    
    assert entity1_class is not None, f"Entity {entity1_name} should exist in MODELS after relationship creation"
    assert entity2_class is not None, f"Entity {entity2_name} should exist in MODELS after relationship creation"
    
    # Basic verification that relationship fields were added
    entity1_fields_dict = entity1_class.model_fields
    entity2_fields_dict = entity2_class.model_fields
    
    # Check that entities have new fields (relationship fields should reference the other entity)
    original_field_count1 = len(entity1_fields)
    original_field_count2 = len(entity2_fields)
    
    # Should have more fields now due to relationships
    assert len(entity1_fields_dict) > original_field_count1, f"Entity1 should have relationship fields added. Original: {original_field_count1}, Current: {len(entity1_fields_dict)}"
    assert len(entity2_fields_dict) > original_field_count2, f"Entity2 should have relationship fields added. Original: {original_field_count2}, Current: {len(entity2_fields_dict)}"
    
    # Verify that relationship fields have correct metadata
    relationship_found = False
    for field_name, field in entity1_fields_dict.items():
        json_extra = getattr(field, 'json_schema_extra', {}) or {}
        if json_extra.get('is_relationship', False):
            relationship_found = True
            assert json_extra.get('target_instance_type') == entity2_name, f"Relationship should target {entity2_name}"
    
    assert relationship_found, f"Entity1 should have at least one relationship field"