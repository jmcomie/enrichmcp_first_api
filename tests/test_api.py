import pytest
import asyncio
from enrichmcp_first_api.api import (
    get_app_dir,
    create_new_project,
    list_projects,
    open_project,
    Project
)


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