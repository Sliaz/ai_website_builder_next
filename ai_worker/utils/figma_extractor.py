"""
Utilities for extracting data from Figma node JSON.
"""
import json
from typing import Any, Dict, List, Optional


def extract_text_content(node: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Recursively extract all text content from a Figma node.
    
    Args:
        node: Figma node JSON
        
    Returns:
        List of dicts with 'text', 'name', and 'path' keys
    """
    text_nodes = []
    
    def traverse(current_node: Dict[str, Any], path: str = "") -> None:
        node_type = current_node.get("type")
        node_name = current_node.get("name", "")
        current_path = f"{path}/{node_name}" if path else node_name
        
        # Text nodes contain the actual text content
        if node_type == "TEXT":
            characters = current_node.get("characters", "")
            if characters:
                text_nodes.append({
                    "text": characters,
                    "name": node_name,
                    "path": current_path,
                    "id": current_node.get("id", "")
                })
        
        # Recurse through children
        children = current_node.get("children", [])
        for child in children:
            traverse(child, current_path)
    
    traverse(node)
    return text_nodes


def extract_image_fills(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Recursively extract all image fills from a Figma node.
    
    Args:
        node: Figma node JSON
        
    Returns:
        List of dicts with image fill information
    """
    image_fills = []
    
    def traverse(current_node: Dict[str, Any], path: str = "") -> None:
        node_name = current_node.get("name", "")
        current_path = f"{path}/{node_name}" if path else node_name
        
        # Check fills for images
        fills = current_node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "IMAGE":
                image_ref = fill.get("imageRef")
                if image_ref:
                    image_fills.append({
                        "imageRef": image_ref,
                        "name": node_name,
                        "path": current_path,
                        "scaleMode": fill.get("scaleMode", "FILL"),
                        "nodeId": current_node.get("id", "")
                    })
        
        # Recurse through children
        children = current_node.get("children", [])
        for child in children:
            traverse(child, current_path)
    
    traverse(node)
    return image_fills


def parse_figma_node(raw_node_json: str) -> Optional[Dict[str, Any]]:
    """
    Parse raw Figma node JSON string.
    
    Args:
        raw_node_json: JSON string from database
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not raw_node_json:
        return None
    
    try:
        return json.loads(raw_node_json)
    except json.JSONDecodeError as e:
        print(f"Error parsing Figma JSON: {e}")
        return None


def extract_component_data(raw_node_json: str) -> Dict[str, Any]:
    """
    Extract all relevant data from a Figma component node.
    
    Args:
        raw_node_json: Raw JSON string from database
        
    Returns:
        Dictionary with extracted text and images
    """
    node = parse_figma_node(raw_node_json)
    if not node:
        return {"texts": [], "images": []}
    
    texts = extract_text_content(node)
    images = extract_image_fills(node)
    
    return {
        "texts": texts,
        "images": images,
        "node_name": node.get("name", ""),
        "node_id": node.get("id", "")
    }
