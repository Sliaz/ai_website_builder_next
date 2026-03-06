import requests
from typing import Literal


class FigmaConnection:
    def __init__(self, figma_token: str, figma_project_key: str, batch_size: int = 50):
        self.figma_token = figma_token
        self.figma_project_key = figma_project_key
        self.batch_size = batch_size

    BASE_FIGMA_URL = "https://api.figma.com/v1"

    def get_developer_variables(self) -> dict:
        url = f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}/variables/local"
        headers = {"X-Figma-Token": self.figma_token}

        response = requests.get(url, headers=headers)

        if response.status_code == 403:
            raise PermissionError(
                "Access denied. Ensure your token has 'file_variables:read' scope "
                "and you are a full member of an Enterprise org."
            )

        if response.status_code == 404:
            raise ValueError(f"File '{self.figma_project_key}' not found.")

        if response.status_code != 200:
            raise RuntimeError(
                f"Figma API error {response.status_code}: {response.text}"
            )

        data = response.json()

        if data.get("err"):
            raise RuntimeError(f"The Figma API raised this error: {data}")

        meta = data.get("meta", {})

        variables = meta.get("variables", {})
        variable_collections = meta.get("variableCollections", {})

        print("\n=== Figma Variables ===")
        print(f"Variables: {variables}")
        print(f"Variable Collections: {variable_collections}")

        return {
            "variables": variables,
            "variable_connections": variable_collections,
        }

    def get_file(self) -> dict:
        response = requests.get(
            f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}",
            headers={"X-Figma-Token": self.figma_token},
        )

        response.raise_for_status()
        data = response.json()
        self.data = data
        return data

    def seed_definitions(self):
        print("\n=== Component Sets ===")
        for node_id, cs in self.data.get("componentSets", {}).items():
            print(
                f"ID: {node_id}, Key: {cs['key']}, Name: {cs['name']}, Description: {cs.get('description', '')}"
            )

        print("\n=== Components ===")
        for node_id, cs in self.data.get("components", {}).items():
            print(
                f"ID: {node_id}, Key: {cs['key']}, Name: {cs['name']}, Description: {cs.get('description', '')}, SetID: {cs.get('componentSetId')}"
            )

    def traverse_pages(self):
        print("\n=== Pages ===")
        document = self.data.get("document", {})
        pages = [n for n in document.get("children", []) if n["type"] == "CANVAS"]

        for page in pages:
            print(f"Page ID: {page['id']}, Name: {page['name']}")

            for frame in page.get("children", []):
                print(
                    f"  Frame: {frame.get('id')} - {frame.get('name')} ({frame.get('type')})"
                )
