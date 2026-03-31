from typing import Dict, TypeDict
from langgraph.graph import StateGraph

class ComponentState(TypeDict):
    component_name: str


def design_component(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the next.js component"""
    pass

def save_component(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the next.js component"""
    # i could save the path in the db so reconstructing this afterwards is easy
    pass

def design_query(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the query for the component"""
    pass

def save_query(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the query for the component"""
    # i could save the path in the db so reconstructing this afterwards is easy
    pass

def design_typescript_type(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the typescript type for the component"""
    pass

def save_typescript_type(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the typescript type for the component"""
    pass

def design_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the sanity schema for the component"""
    pass

def save_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the sanity schema for the component"""
    pass

graph = StateGraph(ComponentState)

graph.set_entry_point("greeting")
graph.set_finish_point("greeting")

app = graph.compile()

result = app.invoke({"website": "bob"})
print(result)

# so I am guessing my state would be made of what I know about a component
# and each node will be what I need to do about it: design the next.js component, add the query for it, typescript type, add it in sanity and add the data from figma into it
# after this is done, i need to: assemble the everything, make sure it works and start working on the design. that would mean invoking nodes with validation logic such as playwright, preceptual hashes and all that kind of stuff