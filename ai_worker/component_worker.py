from typing import TypeDict
from langgraph.graph import StateGraph, START, END
from utils.save_file import save_file

class ComponentState(TypeDict):
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
    pass

def design_query(state: ComponentState, prompt, design_query_model) -> ComponentState:
    """This node is in charge of designing the query for the component"""
    try:
        query = design_query_model(prompt, state)
        state["query_code"] = query
        return state
    except Exception as e:
        print(f"Error designing query: {e}")
        return state

def save_query(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the query for the component"""
    try:
        save_file("./queries", state["query_code"], f"{state['component_name']}", "ts")

        # i could save the path in the db so reconstructing this afterwards is easy

    except Exception as e:
        print(f"Error saving query: {e}")
    pass

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
    pass

def design_sanity_schema(state: ComponentState, prompt, design_sanity_schema_model) -> ComponentState:
    """This node is in charge of designing the sanity schema for the component"""
    try:
        sanity_schema = design_sanity_schema_model(prompt, state)
        state["sanity_schema_code"] = sanity_schema
        return state
    except Exception as e:
        print(f"Error designing sanity schema: {e}")
        return state

def save_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the sanity schema for the component"""
    try:
        save_file("./schemas", state["sanity_schema_code"], f"{state['component_name']}", "ts")
        # i could save the path in the db so reconstructing this afterwards is easy
    except Exception as e:
        print(f"Error saving sanity schema: {e}")
    pass

def populate_component_data(state: ComponentState) -> ComponentState:
    """This node is in charge of populating the component data"""
    try:
        # TODO: Implement component data population logic
        pass
    except Exception as e:
        print(f"Error populating component data: {e}")
    pass

def decide_if_done(state: ComponentState) -> ComponentState:
    """This node is in charge of deciding if the component is done"""
    try:
        state["done"] = state["component_code"] and state["sanity_schema_code"] and state["query_code"] and state["typescript_type_code"] # TODO: implement logic to determine if I am done

        if state["done"]:
            return "debug" # i will have a prompt provided all work done by now, so it can fix it. so this edge points to this function
        else:
            pass
    except Exception as e:
        print(f"Error deciding if done: {e}")
    pass

def debug(state: ComponentState) -> ComponentState:
    """This node is in charge of debugging the component"""
    try:
        # TODO: Implement debugging logic
        pass
    except Exception as e:
        print(f"Error debugging component: {e}")
    pass

graph = StateGraph(ComponentState)

# we first need to dregister all nodes

graph.add_node("design_sanity_schema", design_sanity_schema)
graph.add_node("save_sanity_schema", save_sanity_schema)
graph.add_node("design_query", design_query)
graph.add_node("save_query", save_query)
graph.add_node("design_typescript_type", design_typescript_type)
graph.add_node("save_typescript_type", save_typescript_type)
graph.add_node("design_component", design_component)
graph.add_node("save_component", save_component)
graph.add_node("router", lambda state:state)

# now, the steps:

graph.add_edge(START, "router")
graph.add_conditional_edges(
    "router", 
    decide_if_done,
    {
        "design_query": "design_query",
        "debug": "debug"
    }
)

app = graph.compile()

result = app.invoke({"component_name": "bob"})
print(result)

# so I am guessing my state would be made of what I know about a component
# and each node will be what I need to do about it: design the next.js component, add the query for it, typescript type, add it in sanity and add the data from figma into it
# after this is done, i need to: assemble the everything, make sure it works and start working on the design. that would mean invoking nodes with validation logic such as playwright, preceptual hashes and all that kind of stuff