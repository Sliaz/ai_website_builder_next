import json
import os
from pathlib import Path
from typing import Any
import time

import requests
from sqlmodel import select

from db.migration import (
    Component,
    ComponentSet,
    ComponentUsage,
    Frame,
    Page,
    Variable,
    VariableCollection,
    create_db_and_tables,
)


class FigmaConnection:
    def __init__(
        self,
        figma_token: str,
        figma_project_key: str,
        batch_size: int = 50,
        db_path: str = "figma.db",
        start_canvas_name: str | None = "Delivery",
    ):
        self.figma_token = figma_token
        self.figma_project_key = figma_project_key
        self.batch_size = batch_size
        self.session = create_db_and_tables(db_path)
        self.data: dict[str, Any] | None = None
        self.component_keys_by_node_id: dict[str, str] = {}
        self.debug = os.getenv("DEV", "").lower() in {"1", "true", "yes"}
        self.start_canvas_name = start_canvas_name
        self.figma_screenshots_dir = Path("assets") / "figma_screenshots"
        self.figma_screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.image_batch_size = 10
        self.image_rate_limit_seconds = 0.5
        self.image_max_retries = 5

    BASE_FIGMA_URL = "https://api.figma.com/v1"

    def get_developer_variables(self) -> dict:
        # TODO: figure out why this is not working, even though the account is a paid one
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

        payload = {
            "variables": variables,
            "variable_collections": variable_collections,
        }

        self._persist_variables(payload)

        return payload

    def get_file(self) -> dict:
        response = requests.get(
            f"{self.BASE_FIGMA_URL}/files/{self.figma_project_key}",
            headers={"X-Figma-Token": self.figma_token},
        )

        response.raise_for_status()
        data = response.json()
        self.data = data
        self._persist_file_contents()
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

    def hydrate_components(self):
        """Placeholder for future component extraction into local storage."""
        print("\n=== hydrate_components ===")
        print("This step is not implemented yet. Figma data is loaded in memory only.")

    def _persist_file_contents(self) -> None:
        if not self.data:
            raise ValueError("No Figma data loaded. Call get_file() first.")

        self._persist_component_sets()
        self._persist_components()
        self._persist_pages_frames_and_usages()

    def _persist_component_sets(self) -> None:
        assert self.data is not None
        component_sets = self.data.get("componentSets", {})

        for node_id, payload in component_sets.items():
            key = payload.get("key")
            if not key:
                continue

            component_set = self.session.get(ComponentSet, key)
            if component_set is None:
                component_set = ComponentSet(
                    key=key,
                    node_id=node_id,
                    name=payload.get("name", ""),
                    description=payload.get("description", "") or "",
                )
                self._debug(
                    "ComponentSet created",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component_set.name,
                    },
                )
            else:
                component_set.node_id = node_id
                component_set.name = payload.get("name", component_set.name)
                component_set.description = payload.get(
                    "description", component_set.description
                ) or ""
                self._debug(
                    "ComponentSet updated",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component_set.name,
                    },
                )

            self.session.add(component_set)

        self.session.commit()

    def _debug(self, message: str, payload: dict[str, Any] | None = None) -> None:
        if not self.debug:
            return
        if payload is None:
            print(f"[DEBUG] {message}")
        else:
            print(f"[DEBUG] {message}: {payload}")

    def _persist_components(self) -> None:
        assert self.data is not None
        components = self.data.get("components", {})
        self.component_keys_by_node_id.clear()

        component_payloads: list[tuple[str, dict[str, Any], Component | None, str | None, str]] = []
        node_ids_requiring_images: list[str] = []

        for node_id, payload in components.items():
            key = payload.get("key")
            if not key:
                continue

            self.component_keys_by_node_id[node_id] = key
            component = self.session.get(Component, key)
            updated_at = payload.get("updated_at") or payload.get("updatedAt")

            existing_path = Path(component.screenshot) if component and component.screenshot else None
            has_fresh_cache = (
                component is not None
                and component.updated_at == updated_at
                and existing_path is not None
                and existing_path.exists()
            )

            needs_new_screenshot = not has_fresh_cache
            if needs_new_screenshot:
                node_ids_requiring_images.append(node_id)

            component_payloads.append((node_id, payload, component, updated_at, "needs" if needs_new_screenshot else "cached"))

        screenshot_bytes_map = self._fetch_component_screenshots(node_ids_requiring_images)

        for node_id, payload, component, updated_at, screenshot_strategy in component_payloads:
            key = payload.get("key")
            if not key:
                continue

            comp_name = payload.get("name", "")
            safe_name = comp_name[:50] if len(comp_name) > 50 else comp_name
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_name:
                safe_name = key

            if screenshot_strategy == "needs":
                screenshot_bytes = screenshot_bytes_map.get(node_id)
                if screenshot_bytes is None:
                    raise RuntimeError(f"Missing screenshot bytes for node_id '{node_id}'")

                screenshot_path = self.figma_screenshots_dir / f"{safe_name}.png"
                screenshot_path.write_bytes(screenshot_bytes)
                screenshot_path_str = str(screenshot_path)
            else:
                screenshot_path_str = (
                    component.screenshot if component and component.screenshot else ""
                )

            if component is None:
                component = Component(
                    key=key,
                    node_id=node_id,
                    name=safe_name,
                    description=payload.get("description", "") or "",
                    remote=bool(payload.get("remote", False)),
                    screenshot=screenshot_path_str or None,
                    updated_at=updated_at,
                    component_set_key=payload.get("componentSetId"),
                )
                self._debug(
                    "Component created",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component.name,
                        "component_set_key": component.component_set_key,
                    },
                )
            else:
                component.node_id = node_id
                component.name = payload.get("name", component.name)
                component.description = payload.get("description", component.description) or ""
                component.remote = bool(payload.get("remote", component.remote))
                component.screenshot = screenshot_path_str or component.screenshot
                component.updated_at = updated_at or component.updated_at
                component.component_set_key = payload.get(
                    "componentSetId", component.component_set_key
                )
                self._debug(
                    "Component updated",
                    {
                        "key": key,
                        "node_id": node_id,
                        "name": component.name,
                        "component_set_key": component.component_set_key,
                    },
                )

            self.session.add(component)

        self.session.commit()

    def _persist_pages_frames_and_usages(self) -> None:
        assert self.data is not None
        document = self.data.get("document", {})
        pages = [n for n in document.get("children", []) if n.get("type") == "CANVAS"]

        if self.start_canvas_name:
            target_pages = [
                page
                for page in pages
                if page.get("name", "").strip().lower()
                == self.start_canvas_name.strip().lower()
            ]
            if not target_pages:
                self._debug(
                    "Target canvas not found; processing full document",
                    {"target": self.start_canvas_name},
                )
                target_pages = pages
        else:
            target_pages = pages

        for order, page in enumerate(target_pages):
            if self.start_canvas_name and page not in pages:
                # Should not happen, but guard to avoid inconsistent state.
                continue

            if self.start_canvas_name:
                frames = [
                    f
                    for f in page.get("children", []) or []
                    if f.get("id") and f.get("type") in {"FRAME", "COMPONENT", "SECTION"}
                ]
                for frame_order, frame in enumerate(frames):
                    page_model = self._upsert_page(frame.get("id"), frame.get("name", ""), frame_order)
                    self.session.add(page_model)
                    self._persist_frame(page_model.page_id, frame)
            else:
                page_model = self._upsert_page(page.get("id"), page.get("name", ""), order)
                self.session.add(page_model)

                for frame in page.get("children", []) or []:
                    self._persist_frame(page_model.page_id, frame)

        self.session.commit()

    def _upsert_page(self, page_id: str | None, page_name: str, order: int) -> Page:
        if not page_id:
            raise ValueError("Encountered a page/frame without an id while persisting")

        page_model = self.session.get(Page, page_id)
        if page_model is None:
            page_model = Page(page_id=page_id, page_name=page_name, order=order)
            self._debug("Page created", {"page_id": page_id, "name": page_model.page_name})
        else:
            page_model.page_name = page_name or page_model.page_name
            page_model.order = order
            self._debug("Page updated", {"page_id": page_id, "name": page_model.page_name})

        return page_model

    def _persist_frame(self, page_id: str, frame: dict[str, Any]) -> None:
        frame_id = frame.get("id")
        frame_type = frame.get("type")

        if not frame_id or frame_type not in {"FRAME", "COMPONENT", "SECTION"}:
            # Still recurse to catch nested instances
            for child in frame.get("children", []) or []:
                self._record_component_usages(page_id, None, child)
            return

        bbox = frame.get("absoluteBoundingBox") or {}
        width = bbox.get("width")
        height = bbox.get("height")

        frame_model = self.session.get(Frame, frame_id)
        if frame_model is None:
            frame_model = Frame(
                frame_id=frame_id,
                frame_name=frame.get("name", ""),
                width=width,
                height=height,
                page_id=page_id,
            )
            self._debug(
                "Frame created",
                {"frame_id": frame_id, "name": frame_model.frame_name, "page_id": page_id},
            )
        else:
            frame_model.frame_name = frame.get("name", frame_model.frame_name)
            frame_model.width = width or frame_model.width
            frame_model.height = height or frame_model.height
            frame_model.page_id = page_id
            self._debug(
                "Frame updated",
                {"frame_id": frame_id, "name": frame_model.frame_name, "page_id": page_id},
            )

        self.session.add(frame_model)

        self._record_component_usages(page_id, frame_id, frame)

    def _record_component_usages(
        self, page_id: str, frame_id: str | None, node: dict[str, Any]
    ) -> None:
        node_type = node.get("type")
        if node_type == "INSTANCE" and node.get("componentId"):
            component_key = self.component_keys_by_node_id.get(node["componentId"])
            if component_key:
                usage = self.session.exec(
                    select(ComponentUsage).where(
                        ComponentUsage.instance_node_id == node["id"]
                    )
                ).first()

                if usage is None:
                    usage = ComponentUsage(instance_node_id=node["id"])

                usage.component_key = component_key
                usage.page_id = page_id
                usage.frame_id = frame_id

                self.session.add(usage)
                self._debug(
                    "Component usage recorded",
                    {
                        "instance_node_id": node["id"],
                        "component_key": component_key,
                        "page_id": page_id,
                        "frame_id": frame_id,
                    },
                )

        for child in node.get("children", []) or []:
            self._record_component_usages(page_id, frame_id, child)

    def _persist_variables(self, payload: dict[str, Any]) -> None:
        collections = payload.get("variable_collections") or []
        for collection in collections:
            collection_id = collection.get("id")
            if not collection_id:
                continue

            modes_json = json.dumps(collection.get("modes", []))

            record = self.session.get(VariableCollection, collection_id)
            if record is None:
                record = VariableCollection(
                    collection_id=collection_id,
                    name=collection.get("name", ""),
                    default_mode_id=collection.get("defaultModeId", ""),
                    modes_json=modes_json,
                    remote=bool(collection.get("remote", False)),
                )
                self._debug(
                    "Variable collection created",
                    {"collection_id": collection_id, "name": record.name},
                )
            else:
                record.name = collection.get("name", record.name)
                record.default_mode_id = collection.get(
                    "defaultModeId", record.default_mode_id
                )
                record.modes_json = modes_json or record.modes_json
                record.remote = bool(collection.get("remote", record.remote))
                self._debug(
                    "Variable collection updated",
                    {"collection_id": collection_id, "name": record.name},
                )

            self.session.add(record)

        variables = payload.get("variables") or []
        for variable in variables:
            variable_id = variable.get("id")
            if not variable_id:
                continue

            values_by_mode = json.dumps(variable.get("valuesByMode", {}))
            scopes_json = json.dumps(variable.get("scopes", []))
            code_syntax_json = json.dumps(variable.get("codeSyntax", {}))

            record = self.session.get(Variable, variable_id)
            if record is None:
                record = Variable(
                    variable_id=variable_id,
                    name=variable.get("name", ""),
                    resolved_type=variable.get("resolvedType", ""),
                    values_by_mode_json=values_by_mode,
                    scopes_json=scopes_json,
                    code_syntax_json=code_syntax_json,
                    remote=bool(variable.get("remote", False)),
                    collection_id=variable.get("variableCollectionId", ""),
                )
                self._debug(
                    "Variable created",
                    {
                        "variable_id": variable_id,
                        "name": record.name,
                        "collection_id": record.collection_id,
                    },
                )
            else:
                record.name = variable.get("name", record.name)
                record.resolved_type = variable.get(
                    "resolvedType", record.resolved_type
                )
                record.values_by_mode_json = values_by_mode or record.values_by_mode_json
                record.scopes_json = scopes_json or record.scopes_json
                record.code_syntax_json = code_syntax_json or record.code_syntax_json
                record.remote = bool(variable.get("remote", record.remote))
                record.collection_id = variable.get(
                    "variableCollectionId", record.collection_id
                )
                self._debug(
                    "Variable updated",
                    {
                        "variable_id": variable_id,
                        "name": record.name,
                        "collection_id": record.collection_id,
                    },
                )

            self.session.add(record)

        self.session.commit()

    def _fetch_component_screenshots(self, node_ids: list[str]) -> dict[str, bytes]:
        results: dict[str, bytes] = {}
        if not node_ids:
            return results

        for start in range(0, len(node_ids), self.image_batch_size):
            batch = node_ids[start : start + self.image_batch_size]
            batch_results = self._request_component_images(batch)
            results.update(batch_results)
            time.sleep(self.image_rate_limit_seconds)

        return results

    def _request_component_images(self, node_ids: list[str]) -> dict[str, bytes]:
        url = f"{self.BASE_FIGMA_URL}/images/{self.figma_project_key}"
        headers = {"X-Figma-Token": self.figma_token}
        ids_param = ",".join(node_ids)
        params = {"ids": ids_param, "format": "png", "scale": 2}

        attempt = 0
        while attempt <= self.image_max_retries:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 429:
                wait_time = self.image_rate_limit_seconds * (2**attempt)
                print(
                    "Need to give Figma some time to breathe, so we don't break their limits..."
                )
                time.sleep(wait_time)
                attempt += 1
                continue

            if response.status_code == 403:
                raise PermissionError(
                    "Access denied. Ensure your token has 'file_images:read' scope "
                    "and you are a full member of an Enterprise org."
                )

            if response.status_code == 404:
                raise ValueError(f"File '{self.figma_project_key}' not found.")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Figma API error {response.status_code}: {response.text}"
                )

            images_payload = response.json().get("images", {})
            missing = [node_id for node_id in node_ids if not images_payload.get(node_id)]
            if missing:
                raise RuntimeError(
                    f"Figma did not return image URLs for node_ids: {', '.join(missing)}"
                )

            bytes_map: dict[str, bytes] = {}
            for node_id, image_url in images_payload.items():
                bytes_map[node_id] = self._download_image_bytes(image_url)

            return bytes_map

        raise RuntimeError("Exceeded retries while fetching component screenshots from Figma")

    def _download_image_bytes(self, image_url: str) -> bytes:
        attempt = 0
        while attempt <= self.image_max_retries:
            response = requests.get(image_url)
            if response.status_code == 429:
                wait_time = self.image_rate_limit_seconds * (2**attempt)
                time.sleep(wait_time)
                attempt += 1
                continue

            if response.status_code == 404:
                raise ValueError("Screenshot asset no longer available at provided URL")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Figma image download failed with status {response.status_code}: {response.text}"
                )

            return response.content

        raise RuntimeError("Exceeded retries while downloading component screenshot data")



        
