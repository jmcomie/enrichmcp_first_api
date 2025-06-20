#!/usr/bin/env python3
"""
Command line interface for exploring EnrichMCP First API projects, entities, and instances.
"""

import click
from InquirerPy import prompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts import ListPrompt
from enum import StrEnum
from typing import Optional, List, Type
import asyncio
import functools

from enrichmcp_first_api.api import (
    list_projects,
    open_project,
    list_world_builder_entities,
    list_entity_instances,
    get_instance_by_id,
    get_entity_by_name,
    Project,
    WorldBuilderEntity,
    InstanceWithId
)


class MainMenuOptions(StrEnum):
    LIST_PROJECTS = "list_projects"
    EXPLORE_PROJECT = "explore_project"
    EXIT = "exit"


class ProjectOptions(StrEnum):
    LIST_ENTITIES = "list_entities"
    EXPLORE_ENTITY = "explore_entity"
    BACK = "back"


class EntityOptions(StrEnum):
    LIST_INSTANCES = "list_instances"
    VIEW_INSTANCE = "view_instance"
    BACK = "back"


class InstanceOptions(StrEnum):
    VIEW_DETAILS = "view_details"
    BACK = "back"


class NavigationOptions(StrEnum):
    BACK = "back"
    MAIN_MENU = "main_menu"
    EXIT = "exit"


def run_async_in_thread(coro):
    """Run an async coroutine in a new thread with its own event loop."""
    import threading
    result = None
    exception = None
    
    def run_in_thread():
        nonlocal result, exception
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if exception:
        raise exception
    return result


def display_banner():
    """Display the CLI banner."""
    click.echo("=" * 60)
    click.echo("  EnrichMCP First API Explorer")
    click.echo("  Interactive CLI for Projects, Entities & Instances")
    click.echo("=" * 60)
    click.echo()



def show_projects_list():
    """Display list of all projects."""
    projects = list_projects()
    if not projects:
        click.echo("No projects found.")
        return []
    
    click.echo("\nAvailable Projects:")
    click.echo("-" * 40)
    for i, project in enumerate(projects, 1):
        click.echo(f"{i:2d}. {project.name} ({project.id})")
        click.echo(f"     Theme: {project.theme}")
    click.echo()
    return projects


def show_entities_list(project_id: str):
    """Display list of all entities in the current project."""
    try:
        async def _show_entities():
            await open_project(project_id)
            return await list_world_builder_entities()
        
        entities = run_async_in_thread(_show_entities())
        
        if not entities:
            click.echo("No entities found in this project.")
            return []
        
        click.echo(f"\nEntities in project '{project_id}':")
        click.echo("-" * 40)
        for i, entity in enumerate(entities, 1):
            click.echo(f"{i:2d}. {entity.__name__}")
            if hasattr(entity, '__doc__') and entity.__doc__:
                click.echo(f"     {entity.__doc__}")
        click.echo()
        return entities
    except Exception as e:
        click.echo(f"Error loading entities: {e}")
        return []


def show_instances_list(entity_name: str):
    """Display list of all instances for an entity."""
    try:
        instances = list_entity_instances(entity_name)
        
        if not instances:
            click.echo(f"No instances found for entity '{entity_name}'.")
            return []
        
        click.echo(f"\nInstances of '{entity_name}':")
        click.echo("-" * 40)
        for instance_with_id in instances:
            click.echo(f"ID {instance_with_id.id:2d}: {type(instance_with_id.instance).__name__}")
            # Show a few key fields if available
            fields = instance_with_id.instance.model_fields
            field_preview = []
            for field_name, field in list(fields.items())[:3]:  # Show first 3 fields
                try:
                    value = getattr(instance_with_id.instance, field_name)
                    if isinstance(value, str) and len(value) > 30:
                        value = value[:27] + "..."
                    field_preview.append(f"{field_name}: {value}")
                except:
                    pass
            if field_preview:
                click.echo(f"     {', '.join(field_preview)}")
        click.echo()
        return instances
    except Exception as e:
        click.echo(f"Error loading instances: {e}")
        return []


def show_instance_details(instance_id: int):
    """Display detailed information about a specific instance."""
    try:
        instance = get_instance_by_id(instance_id)
        if not instance:
            click.echo(f"Instance with ID {instance_id} not found.")
            return
        
        click.echo(f"\nInstance Details (ID: {instance_id})")
        click.echo("=" * 50)
        click.echo(f"Type: {type(instance).__name__}")
        click.echo()
        
        # Show all fields
        fields = instance.model_fields
        for field_name, field in fields.items():
            try:
                value = getattr(instance, field_name)
                field_type = field.annotation.__name__ if hasattr(field.annotation, '__name__') else str(field.annotation)
                
                # Check if this is a relationship field
                json_extra = getattr(field, 'json_schema_extra', {}) or {}
                is_relationship = json_extra.get('is_relationship', False)
                
                if is_relationship:
                    target_type = json_extra.get('target_instance_type', 'Unknown')
                    click.echo(f"{field_name} ({field_type}) [Relationship to {target_type}]: {value}")
                else:
                    click.echo(f"{field_name} ({field_type}): {value}")
                
                if field.description:
                    click.echo(f"  └─ {field.description}")
            except Exception as e:
                click.echo(f"{field_name}: <Error accessing field: {e}>")
        click.echo()
    except Exception as e:
        click.echo(f"Error loading instance details: {e}")


def explore_entity_menu(entity: Type[WorldBuilderEntity], project_id: str):
    """Interactive menu for exploring a specific entity."""
    while True:
        click.echo(f"\n--- Entity: {entity.__name__} ---")
        
        questions = [
            {
                'type': 'list',
                'name': 'action',
                'message': "What would you like to do?",
                'choices': [
                    Choice(EntityOptions.LIST_INSTANCES, name=f"List all instances of {entity.__name__}"),
                    Choice(EntityOptions.VIEW_INSTANCE, name="View specific instance"),
                    Choice(EntityOptions.BACK, name="Back to entities list"),
                ]
            }
        ]
        
        answers = prompt(questions)
        if not answers:
            break
            
        action = answers['action']
        
        if action == EntityOptions.LIST_INSTANCES:
            instances = show_instances_list(entity.__name__)
            if instances:
                input("\nPress Enter to continue...")
                
        elif action == EntityOptions.VIEW_INSTANCE:
            instances = show_instances_list(entity.__name__)
            if instances:
                # Let user select an instance
                instance_choices = [
                    Choice(inst.id, name=f"ID {inst.id}: {type(inst.instance).__name__}")
                    for inst in instances
                ]
                instance_choices.append(Choice(None, name="Cancel"))
                
                instance_questions = [
                    {
                        'type': 'list',
                        'name': 'instance_id',
                        'message': "Select an instance to view:",
                        'choices': instance_choices
                    }
                ]
                
                instance_answers = prompt(instance_questions)
                if instance_answers and instance_answers['instance_id'] is not None:
                    show_instance_details(instance_answers['instance_id'])
                    input("\nPress Enter to continue...")
                    
        elif action == EntityOptions.BACK:
            break


def explore_project_menu(project: Project):
    """Interactive menu for exploring a specific project."""
    while True:
        click.echo(f"\n--- Project: {project.name} ({project.id}) ---")
        click.echo(f"Theme: {project.theme}")
        
        questions = [
            {
                'type': 'list',
                'name': 'action',
                'message': "What would you like to do?",
                'choices': [
                    Choice(ProjectOptions.LIST_ENTITIES, name="List all entities"),
                    Choice(ProjectOptions.EXPLORE_ENTITY, name="Explore specific entity"),
                    Choice(ProjectOptions.BACK, name="Back to projects list"),
                ]
            }
        ]
        
        answers = prompt(questions)
        if not answers:
            break
            
        action = answers['action']
        
        if action == ProjectOptions.LIST_ENTITIES:
            entities = show_entities_list(project.id)
            if entities:
                input("\nPress Enter to continue...")
                
        elif action == ProjectOptions.EXPLORE_ENTITY:
            entities = show_entities_list(project.id)
            if entities:
                # Let user select an entity
                entity_choices = [
                    Choice(entity, name=entity.__name__) for entity in entities
                ]
                entity_choices.append(Choice(None, name="Cancel"))
                
                entity_questions = [
                    {
                        'type': 'list',
                        'name': 'entity',
                        'message': "Select an entity to explore:",
                        'choices': entity_choices
                    }
                ]
                
                entity_answers = prompt(entity_questions)
                if entity_answers and entity_answers['entity'] is not None:
                    explore_entity_menu(entity_answers['entity'], project.id)
                    
        elif action == ProjectOptions.BACK:
            break


def main_menu():
    """Main interactive menu."""
    while True:
        click.echo("\n--- Main Menu ---")
        
        questions = [
            {
                'type': 'list',
                'name': 'action',
                'message': "What would you like to do?",
                'choices': [
                    Choice(MainMenuOptions.LIST_PROJECTS, name="List all projects"),
                    Choice(MainMenuOptions.EXPLORE_PROJECT, name="Explore a project"),
                    Choice(MainMenuOptions.EXIT, name="Exit"),
                ]
            }
        ]
        
        answers = prompt(questions)
        if not answers:
            break
            
        action = answers['action']
        
        if action == MainMenuOptions.LIST_PROJECTS:
            projects = show_projects_list()
            if projects:
                input("\nPress Enter to continue...")
                
        elif action == MainMenuOptions.EXPLORE_PROJECT:
            projects = show_projects_list()
            if projects:
                # Let user select a project
                project_choices = [
                    Choice(proj, name=f"{proj.name} ({proj.id})") for proj in projects
                ]
                project_choices.append(Choice(None, name="Cancel"))
                
                project_questions = [
                    {
                        'type': 'list',
                        'name': 'project',
                        'message': "Select a project to explore:",
                        'choices': project_choices
                    }
                ]
                
                project_answers = prompt(project_questions)
                if project_answers and project_answers['project'] is not None:
                    explore_project_menu(project_answers['project'])
                    
        elif action == MainMenuOptions.EXIT:
            click.echo("\nGoodbye!")
            break


@click.command()
@click.option('--project', '-p', help='Project ID to open directly')
@click.option('--entity', '-e', help='Entity name to explore directly (requires --project)')
@click.option('--instance', '-i', type=int, help='Instance ID to view directly')
def cli(project: Optional[str], entity: Optional[str], instance: Optional[int]):
    """
    Interactive CLI for exploring EnrichMCP First API projects, entities, and instances.
    
    Examples:
        cli                          # Interactive menu
        cli -p my_project            # Open project directly
        cli -p my_project -e Hero    # Explore Hero entity in my_project
        cli -i 5                     # View instance with ID 5
    """
    display_banner()
    
    # Handle direct access modes
    if instance is not None:
        show_instance_details(instance)
        return
    
    try:
        if project and entity:
            # Direct entity exploration
            async def _run_entity():
                await open_project(project)
                return get_entity_by_name(entity)
            
            entity_class = run_async_in_thread(_run_entity())
            if entity_class:
                explore_entity_menu(entity_class, project)
            else:
                click.echo(f"Entity '{entity}' not found in project '{project}'")
            return
        
        if project:
            # Direct project exploration
            async def _run_project():
                return await open_project(project)
            
            proj = run_async_in_thread(_run_project())
            if proj:
                explore_project_menu(proj)
            else:
                click.echo(f"Project '{project}' not found")
            return
        
        # Interactive mode
        main_menu()
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == '__main__':
    cli()