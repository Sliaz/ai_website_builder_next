import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from ai_worker.utils.save_file import save_file

# ! i just realized that the website needs to be assembled as it is built, since I can't actually test it otherwise
# ! so this worker needs to be able to assemble the website as it goes

class ComponentState(TypedDict):
    key: str # not sure this is actually useful
    node_id: str # not sure this is actually useful
    component_name: str
    component_description: str # not sure this is actually useful
    raw_node_json: str # ! component data, very important
    width: int
    height: int
    component_set_key: str # not sure this is actually useful here
    figma_screenshot: str
    component_code: str
    query_code: str
    typescript_type_code: str
    sanity_schema_code: str
    sanity_schema_filename: str
    project_path: str
    done: bool


def design_component(state: ComponentState, prompt: str, design_component_model) -> ComponentState:
    """This node is in charge of designing the next.js component"""
    # this will be provided by the factory, to use the desired ai model
    try:
        component = design_component_model(prompt, state)
        state["component_code"] = component
        return state
    except Exception as e:
        print(f"Error designing component: {e}")
        return state

def save_component(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the next.js component"""
    try:
        save_file("./components", state["component_code"], f"{state['component_name']}", "tsx")
        # i could save the path in the db so reconstructing this afterwards is easy
    except Exception as e:
        print(f"Error saving component: {e}")
    return state

def design_query(state: ComponentState, prompt, design_query_model) -> ComponentState:
    """This node is in charge of designing the query for the component"""
    try:
        project_path = state.get("project_path", "")
        queries_path = os.path.join(project_path, "frontend", "sanity", "lib", "queries.ts")

        with open(queries_path, "r") as f:
            queries = f.read()
        
        prompt = f"{prompt}\n\nExisting queries:\n{queries}"
        
        query = design_query_model(prompt, state, queries)
        state["query_code"] = query # in here I now have the getPageQuery var inside the string
        return state
    except Exception as e:
        print(f"Error designing query: {e}")
        return state

def save_query(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the query for the component"""

    import os
    import re

    try: 
        project_path = state.get("project_path", "")
        queries_path = os.path.join(project_path, "frontend", "sanity", "lib", "queries.ts")

        new_getPageQuery = state.get("query_code", "")

        if not new_getPageQuery:
            print(f"No query code found in state")
            return state

        with open(queries_path, "r") as f:
            existing_queries = f.read()
        
        # Replace the entire getPageQuery variable declaration
        # Pattern matches: export const getPageQuery = ... up to the semicolon
        pattern = r'export\s+const\s+getPageQuery\s*=\s*.*?;'
        
        if re.search(pattern, existing_queries, re.DOTALL):
            updated_queries = re.sub(pattern, new_getPageQuery.strip(), existing_queries, flags=re.DOTALL)
            
            with open(queries_path, "w") as f:
                f.write(updated_queries)
            
            print(f"Successfully replaced getPageQuery in {queries_path}")
        else:
            print(f"getPageQuery variable not found in {queries_path}")
        
        return state

    except Exception as e:
        print(f"Error saving query: {e}")
        return state

def design_typescript_type(state: ComponentState, prompt, design_typescript_type_model) -> ComponentState:
    """This node is in charge of designing the typescript type for the component"""
    try:
        typescript_type = design_typescript_type_model(prompt, state)
        state["typescript_type_code"] = typescript_type
        return state
    except Exception as e:
        print(f"Error designing typescript type: {e}")
        return state

def save_typescript_type(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the typescript type for the component"""
    try:
        save_file("./types", state["typescript_type_code"], f"{state['component_name']}", "ts")
        # i could save the path in the db so reconstructing this afterwards is easy
    except Exception as e:
        print(f"Error saving typescript type: {e}")
    return state

def design_sanity_schema(state: ComponentState, prompt, design_sanity_schema_model) -> ComponentState:
    """This node is in charge of designing the sanity schema for the component"""
    import json
    try:
        response = design_sanity_schema_model(prompt, state)
        
        # Log the raw AI response
        print("\n" + "="*80)
        print(f"RAW AI RESPONSE for {state.get('component_name', 'UNKNOWN')}:")
        print("="*80)
        print(response)
        print("="*80 + "\n")
        
        parsed_response = json.loads(response)
        
        filename = parsed_response.get("filename", "").strip()
        schema = parsed_response.get("schema", "").strip()
        
        # Fallback to component_name if filename is empty
        if not filename:
            filename = state.get("component_name", "unknown_component")
            print(f"⚠️  Warning: AI did not provide filename, using component_name: {filename}")
        
        if not schema:
            print(f"⚠️  Warning: AI provided empty schema for {filename}")
        
        state["sanity_schema_code"] = schema
        state["sanity_schema_filename"] = filename
        
        print(f"✓ Parsed: filename='{filename}', schema_length={len(schema)} chars")
        
        return state
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response: {e}")
        print(f"Raw response: {response}")
        # Set fallback values
        state["sanity_schema_filename"] = state.get("component_name", "unknown_component")
        state["sanity_schema_code"] = ""
        return state
    except Exception as e:
        print(f"❌ Error designing sanity schema: {e}")
        import traceback
        traceback.print_exc()
        # Set fallback values
        state["sanity_schema_filename"] = state.get("component_name", "unknown_component")
        state["sanity_schema_code"] = ""
        return state

def save_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the sanity schema for the component"""
    import os
    try:
        project_path = state.get("project_path", "")
        filename = state.get("sanity_schema_filename", "").strip()
        schema_code = state.get("sanity_schema_code", "").strip()
        
        # Validate filename
        if not filename:
            filename = state.get("component_name", "unknown_component")
            print(f"⚠️  save_sanity_schema: No filename in state, using component_name: {filename}")
        
        # Validate schema content
        if not schema_code:
            print(f"❌ save_sanity_schema: Schema code is empty for {filename}, skipping save")
            return state
        
        print(f"📝 Saving schema: filename='{filename}', content_length={len(schema_code)} chars")
        
        # Save schema to /studio/src/schemaTypes/objects/{filename}.ts
        schema_dir = os.path.join(project_path, "studio", "src", "schemaTypes", "objects")
        os.makedirs(schema_dir, exist_ok=True)
        schema_path = os.path.join(schema_dir, f"{filename}.ts")
        
        with open(schema_path, "w") as f:
            f.write(schema_code)
        
        print(f"Saved schema to: {schema_path}")
        
        # Update /studio/src/schemaTypes/index.ts to register the schema
        index_path = os.path.join(project_path, "studio", "src", "schemaTypes", "index.ts")
        
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                index_content = f.read()
            
            # Extract the variable name from the schema (looks for 'export const variableName')
            var_match = re.search(r'export const (\w+) = defineType', schema_code)
            if var_match:
                var_name = var_match.group(1)
                
                # Add import if not already present
                import_statement = f"import {{{var_name}}} from './objects/{filename}'"
                if import_statement not in index_content:
                    # Find the last import line
                    import_lines = [line for line in index_content.split('\n') if line.strip().startswith('import')]
                    if import_lines:
                        last_import = import_lines[-1]
                        index_content = index_content.replace(last_import, f"{last_import}\n{import_statement}")
                    else:
                        # No imports found, add at the beginning
                        index_content = f"{import_statement}\n\n{index_content}"
                
                # Add to schemaTypes array in the Objects section if not already present
                if var_name not in index_content or f"{var_name}," not in index_content:
                    # Find the Objects comment section
                    objects_match = re.search(r'(// Objects\s*\n)', index_content)
                    if objects_match:
                        # Insert after the Objects comment
                        insert_pos = objects_match.end()
                        # Find the next line to insert after (first object entry)
                        remaining = index_content[insert_pos:]
                        first_object_match = re.search(r'(\s+\w+,\s*\n)', remaining)
                        if first_object_match:
                            actual_insert_pos = insert_pos + first_object_match.end()
                            index_content = index_content[:actual_insert_pos] + f"  {var_name},\n" + index_content[actual_insert_pos:]
                        else:
                            # No objects yet, insert right after comment
                            index_content = index_content[:insert_pos] + f"  {var_name},\n" + index_content[insert_pos:]
                
                # Write updated index.ts
                with open(index_path, "w") as f:
                    f.write(index_content)

                # Register this page block option inside page.ts
                page_schema_path = os.path.join(project_path, "studio", "src", "schemaTypes", "documents", "page.ts")

                if os.path.exists(page_schema_path):
                    with open(page_schema_path, "r") as f:
                        page_schema_content = f.read()
                    
                    # Check if this schema type is already registered in page builder
                    if f"type: '{var_name}'" not in page_schema_content:
                        # Find the pageBuilder field's 'of' array - flexible regex
                        blocks_match = re.search(r"name:\s*'pageBuilder',?\s*\n\s*title:\s*'[Pp]age\s+[Bb]uilder',?\s*\n\s*type:\s*'array',?\s*\n\s*of:\s*\[", page_schema_content)
                        if blocks_match:
                            insert_pos = blocks_match.end()
                            # Insert after the opening bracket, before any existing types
                            page_schema_content = page_schema_content[:insert_pos] + f"\n        {{type: '{var_name}'}}," + page_schema_content[insert_pos:]
                            
                            with open(page_schema_path, "w") as f:
                                f.write(page_schema_content)
                            
                            print(f"Registered {var_name} in page.ts pageBuilder")
                        else:
                            print(f"⚠️  Could not find pageBuilder field in page.ts to register {var_name}")
                
                print(f"Registered {var_name} in index.ts")
        
    except Exception as e:
        print(f"Error saving sanity schema: {e}")
    
    return state

def populate_component_data(state: ComponentState) -> ComponentState:
    """
    Populate Sanity CMS with component data extracted from Figma.
    Uses global project state for configuration and database for component data.
    """
    from sqlmodel import select
    from db.migration import SectionComponent, Page, ExtractedImage, create_db_and_tables
    from ai_worker.utils.figma_extractor import extract_component_data
    from ai_worker.utils.sanity_client import SanityClient
    from ai_worker.utils.global_state import get_state
    
    try:
        # Get global project state
        project_state = get_state()
        
        # Validate Sanity configuration from global state
        if not project_state.has_sanity_config():
            print("⚠️  Sanity credentials not configured in project state. Skipping data population.")
            print("   Run project initialization first or set credentials manually.")
            return state
        
        # Extract component information from state
        node_id = state.get("node_id")
        schema_filename = state.get("sanity_schema_filename")
        
        if not node_id or not schema_filename:
            print("⚠️  Missing required component data in state")
            return state
        
        print(f"\n=== Populating data for component: {state['component_name']} ===")
        
        # 1. Query database for component, page, and embedded images
        # This uses data already extracted and saved by figma_connection.py
        print("  → Querying database for component data...")
        session = create_db_and_tables("figma.db")
        
        try:
            # Find the section component (already has raw_node_json and screenshot)
            section = session.exec(
                select(SectionComponent).where(SectionComponent.node_id == node_id)
            ).first()
            
            if not section:
                print(f"⚠️  Section component {node_id} not found in database")
                return state
            
            # Get the page this component belongs to
            page = session.exec(
                select(Page).where(Page.page_id == section.page_id)
            ).first()
            
            if not page:
                print(f"⚠️  Page {section.page_id} not found in database")
                return state
            
            # Get embedded images for this section (extracted by figma_connection.py)
            embedded_images = session.exec(
                select(ExtractedImage).where(ExtractedImage.section_node_id == node_id)
            ).all()
            
            print(f"  → Component belongs to page: '{page.page_name}'")
            print(f"  → Screenshot: {section.screenshot}")
            print(f"  → Embedded images: {len(embedded_images)}")
            
            # Use the raw_node_json from database (already stored by figma_connection)
            stored_json = section.raw_node_json
            
        finally:
            session.close()
        
        # 2. Extract text from the stored Figma JSON
        print("  → Extracting text data from stored Figma JSON...")
        component_data = extract_component_data(stored_json)
        texts = component_data.get("texts", [])
        
        print(f"  → Found {len(texts)} text elements and {len(embedded_images)} embedded images")
        
        # 3. Initialize Sanity client using global state
        print("  → Connecting to Sanity CMS...")
        sanity_client = SanityClient(
            project_id=project_state.sanity_project_id,
            dataset=project_state.sanity_dataset,
            token=project_state.sanity_token,
            api_version=project_state.sanity_api_version
        )
        
        # 4. Upload embedded images to Sanity and get asset references
        print("  → Uploading embedded images to Sanity...")
        image_assets = {}
        for img in embedded_images:
            if not img.local_path:
                continue
            
            try:
                # Upload image to Sanity
                asset = sanity_client.upload_image(
                    img.local_path,
                    filename=f"{img.node_name or 'image'}.png"
                )
                image_assets[img.node_id] = asset
                print(f"    → Uploaded {img.node_name}: {asset.get('_id', 'unknown')}")
            except Exception as e:
                print(f"    ✗ Failed to upload {img.node_name}: {str(e)[:50]}")
        
        # 5. Create page slug from page name
        page_slug = page.page_name.lower().replace(" ", "-").replace("_", "-")
        
        # 6. Build the component block with extracted data
        print("  → Building component block...")
        block = {
            "_type": schema_filename,
            "_key": node_id.replace(":", "_"),  # Sanity requires alphanumeric keys
        }
        
        # Add text fields to the block
        for idx, text_item in enumerate(texts):
            field_name = text_item["name"].lower().replace(" ", "_").replace("-", "_")
            if not field_name or field_name == "_":
                field_name = f"text_{idx}"
            block[field_name] = text_item["text"]
        
        # Add uploaded image references
        for idx, img in enumerate(embedded_images):
            asset = image_assets.get(img.node_id)
            if not asset:
                continue
                
            field_name = img.node_name.lower().replace(" ", "_").replace("-", "_")
            if not field_name or field_name == "_":
                field_name = f"image_{idx}"
            
            block[field_name] = {
                "_type": "image",
                "asset": {
                    "_type": "reference",
                    "_ref": asset.get("_id", "")
                }
            }
        
        print(f"  → Block fields: {list(block.keys())}")
        
        # 7. Create or update the page in Sanity
        print(f"  → Creating/updating page '{page_slug}' in Sanity...")
        try:
            result = sanity_client.create_or_update_page(
                title=page.page_name,
                slug=page_slug,
                block=block
            )
            print(f"  ✓ Successfully added block to page '{page_slug}'")
            print(f"    Page ID: {result.get('_id', 'unknown')}")
        except Exception as e:
            print(f"  ✗ Error creating/updating Sanity page: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"=== Data population complete for {state['component_name']} ===\n")
        
    except Exception as e:
        print(f"Error populating component data: {e}")
        import traceback
        traceback.print_exc()
    
    return state

def decide_if_done(state: ComponentState) -> str:
    """This node is in charge of deciding if the component is done"""
    try:
        state["done"] = bool(state.get("component_code")) and bool(state.get("sanity_schema_code")) and bool(state.get("query_code")) and bool(state.get("typescript_type_code"))

        if state["done"]:
            return "debug"
        else:
            return "design_sanity_schema"
    except Exception as e:
        print(f"Error deciding if done: {e}")
        return "END"

def debug(state: ComponentState) -> ComponentState:
    """This node is in charge of debugging the component"""
    try:
        # TODO: Implement debugging logic
        pass
    except Exception as e:
        print(f"Error debugging component: {e}")
    return state

# Graph setup - only compile when actually needed, not on import
def create_component_workflow():
    """Create and return the component workflow graph"""
    graph = StateGraph(ComponentState)

    # Register all nodes
    graph.add_node("design_sanity_schema", design_sanity_schema)
    graph.add_node("save_sanity_schema", save_sanity_schema)
    graph.add_node("design_query", design_query)
    graph.add_node("save_query", save_query)
    graph.add_node("design_typescript_type", design_typescript_type)
    graph.add_node("save_typescript_type", save_typescript_type)
    graph.add_node("design_component", design_component)
    graph.add_node("save_component", save_component)
    graph.add_node("debug", debug)
    graph.add_node("router", lambda state: state)

    # Define edges
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router", 
        decide_if_done,
        {
            "design_sanity_schema": "design_sanity_schema",
            "design_query": "design_query",
            "debug": "debug",
            "END": END
        }
    )
    
    # Add edges to END for completed nodes
    graph.add_edge("debug", END)
    
    return graph.compile()

# Uncomment below to test the workflow
# if __name__ == "__main__":
#     app = create_component_workflow()
#     result = app.invoke({"component_name": "bob"})
#     print(result)

# so I am guessing my state would be made of what I know about a component
# and each node will be what I need to do about it: design the next.js component, add the query for it, typescript type, add it in sanity and add the data from figma into it
# after this is done, i need to: assemble the everything, make sure it works and start working on the design. that would mean invoking nodes with validation logic such as playwright, preceptual hashes and all that kind of stuff