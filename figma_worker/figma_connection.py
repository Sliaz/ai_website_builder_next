import requests
from typing import Literal

class FigmaConnection():
    # i will connect to figma to read neceessary data from here

    def __init__(self, figma_token: str, figma_project_key: str, batch_size: int = 50):
        self.figma_token = figma_token
        self.figma_proejct_key = figma_proejct_key
        self.batch_size = self.batch_size

    BASE_FIGMMA_URL = "https://api.figma.com/v1"
        

    def get_developer_variables(self) -> dict:
        # we will use this function to get the vars already set

        url = f"{BASE_URL}/files/{self.figma_project_key}/variables/local"
        headers = {"X-Figma-Token": self.figma_token}

        response = requests.get(url, headers=headers)

        if response.status_code == 403:
            raise PermissionError(
                "Access denied. Ensure your token has 'file_variables:read' scope "
                "and you are a full member of an Enterprise org."
            )

        if response.status_code == 404:
            raise ValueError(f"File '{file_key}' not found.")
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Figma API error {response.status_code}: {response.text}"
            )

        data = response.json()

        if data.get(error):
            raise RuntimeError(f"The Figma API raised this error: {data}")

        meta = data.get("meta", {})

        # we will need to somehow structure this data later and save it in the tailwind config file, so the AI will know how to use them
        # ? should we pass the whole tailwind.config.ts to the AI?

        return {
            "variables": meta.get("variables", {}),
            "variable_connections": meta.get("variableCollections", {})
        }

    def get_file(self) -> dict:
        response = requests.get(
            f"{BASE_FIGMMA_URL}/files/{self.figma_proejct_key}",
            headers={"X-Figma-Token": self.figma_token},
        )

        data = response.json()
        self.data = data
        return data

    def seed_definitions(self):
        # this function returns all components and component sets (for example, states of a button)
        for node_id, cs in self.data.get("componentSets", {}).items():
            # TODO: insert them into the database here
            print(node_id, cs["key"], cs["name"], cs.get("descripiton", ""))

        # and in here I am getting all components themselves

        for node_id, cs in self.data.get("components", {}).items():
            # TODO: insert these into the database
            print(cs["key", node_id, cs["name"], cs.get("description", ""), cs.get("componentSetId")])

    def traverse_pages(self):
        # in here, we will traverse each website page (each canvas) and get were each component is used

        pages = [n for n in document.get("children", []) if n["type"] == "CANVAS"]

        for page in pages:
            # TODO: insert the page into the database here
            print(page["id"], page["name"])

            for frame in page.get("children", []):
                pass

    def _walk_node(node: dict, page_id: str, frame_id: str, frame_name: str):
        # so each node can be a different type. we will go for each type of node

        node_type = node.get("type")

        if node_type == "INSTANCE":
            # we first need to keep in mind what page this component is used on
            main_comp = node.get("mainComponent") or {}
            comp_key = main_comp.get("key")

            if comp_key:
                # TODO: insert it into the database
                print(comp_key)

        for child in node.get("children", []):
            # i am basically building a tree with the parent node set to each page of the website
            _walk_node(child, page_id, frame_id, frame_name)

    def hydrate_component(self) -> dict:
        # in here I will be getting data about each component that I will be sending to the AI
        
        rows = []

        # TODO: read all components from the database

        if not rows:
            print("All components data was read already")
            return

        for i in range(0, len(rows), self.batch_size):
            batch = rows[i : i + batch_size]
            ids = ",".join(r[0] for r in batch)

            response = requests.get(
                f"{BASE_URL}/files/{file_key}/nodes",
                headers={"X-Figma-Token": token},
                params={"ids": ids},
            )

            resp.raise_for_status()
            nodes = resp.json().get("nodes", {})

            for node_id, comp_key in batch:
                node_data = nodes.get(node_id)
                if node_data:
                    # TODO: insert raw json data into the database
                    pass

            print(f"[hydrate] Batch {i // batch_size + 1}: {len(batch)} components hydrated.")

