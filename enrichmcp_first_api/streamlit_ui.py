import streamlit as st
import asyncio
from enrichmcp_first_api.api import (
    list_projects, 
    open_project, 
    list_world_builder_entities,
    list_entity_instances,
    get_instance_by_id
)

def run_async(func, *args, **kwargs):
    """Helper to run async functions in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(func(*args, **kwargs))

def main():
    st.set_page_config(page_title="WorldBuilder Browser", page_icon="🌍")
    st.title("🌍 WorldBuilder Browser")
    
    # Project Selection
    st.header("📁 Select Project")
    projects = list_projects()
    
    if not projects:
        st.error("No projects found!")
        return
    
    project_names = [f"{p.name} ({p.id})" for p in projects]
    selected_idx = st.selectbox("Choose project:", range(len(project_names)), 
                               format_func=lambda x: project_names[x])
    
    if st.button("Open Project"):
        project = projects[selected_idx]
        result = run_async(open_project, project.id)
        if result:
            st.success(f"✅ Opened: {project.name}")
            st.session_state.project_opened = True
        else:
            st.error("Failed to open project")
            return
    
    # Only show entities if project is opened
    if not st.session_state.get('project_opened', False):
        st.info("👆 Please open a project first")
        return
    
    # Entity Selection
    st.header("📋 Select Entity Type")
    entities = run_async(list_world_builder_entities)
    
    if not entities:
        st.warning("No entities found")
        return
    
    entity_names = [entity.__name__ for entity in entities]
    selected_entity = st.selectbox("Choose entity type:", entity_names)
    
    # Show Instances
    if selected_entity:
        st.header(f"📝 {selected_entity} Instances")
        instances = list_entity_instances(selected_entity)
        
        if not instances:
            st.info("No instances found")
        else:
            st.write(f"Found {len(instances)} instances:")
            
            for inst in instances:
                with st.expander(f"ID: {inst.id}"):
                    # Get the actual instance data
                    data = inst.instance.model_dump()
                    
                    # Display each field
                    for key, value in data.items():
                        st.write(f"**{key}:** {value}")

if __name__ == "__main__":
    main()