"""
Sanity CMS client for creating and updating documents.
"""
import requests
from typing import Any, Dict, List, Optional
import json


class SanityClient:
    """Client for interacting with Sanity CMS via HTTP API."""
    
    def __init__(self, project_id: str, dataset: str, token: str, api_version: str = "2024-01-01"):
        """
        Initialize Sanity client.
        
        Args:
            project_id: Sanity project ID
            dataset: Dataset name (e.g., 'production')
            token: Auth token with write permissions
            api_version: API version to use
        """
        self.project_id = project_id
        self.dataset = dataset
        self.token = token
        self.api_version = api_version
        self.base_url = f"https://{project_id}.api.sanity.io/v{api_version}/data"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_page_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a page document by its slug.
        
        Args:
            slug: Page slug
            
        Returns:
            Page document or None if not found
        """
        query = f'*[_type == "page" && slug.current == "{slug}"][0]'
        url = f"{self.base_url}/query/{self.dataset}"
        params = {"query": query}
        
        response = requests.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        
        result = response.json()
        return result.get("result")
    
    def create_page(self, title: str, slug: str, page_builder: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a new page document.
        
        Args:
            title: Page title
            slug: Page slug
            page_builder: Optional array of page builder blocks
            
        Returns:
            Created page document
        """
        mutations = [{
            "create": {
                "_type": "page",
                "title": title,
                "slug": {
                    "_type": "slug",
                    "current": slug
                },
                "pageBuilder": page_builder or []
            }
        }]
        
        url = f"{self.base_url}/mutate/{self.dataset}"
        response = requests.post(
            url,
            headers=self._get_headers(),
            json={"mutations": mutations}
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("results", [{}])[0].get("document", {})
    
    def add_block_to_page(self, page_id: str, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a block to a page's pageBuilder array.
        
        Args:
            page_id: Sanity document _id
            block: Block object to add
            
        Returns:
            Updated page document
        """
        mutations = [{
            "patch": {
                "id": page_id,
                "insert": {
                    "after": "pageBuilder[-1]",
                    "items": [block]
                }
            }
        }]
        
        url = f"{self.base_url}/mutate/{self.dataset}"
        response = requests.post(
            url,
            headers=self._get_headers(),
            json={"mutations": mutations}
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("results", [{}])[0].get("document", {})
    
    def create_or_update_page(
        self,
        title: str,
        slug: str,
        block: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a page if it doesn't exist, or add a block to existing page.
        
        Args:
            title: Page title
            slug: Page slug
            block: Block to add to the page
            
        Returns:
            Page document
        """
        existing_page = self.get_page_by_slug(slug)
        
        if existing_page:
            print(f"  → Page '{slug}' exists, adding block...")
            return self.add_block_to_page(existing_page["_id"], block)
        else:
            print(f"  → Creating new page '{slug}'...")
            return self.create_page(title, slug, [block])
    
    def upload_image(self, image_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload an image to Sanity.
        
        Args:
            image_path: Local path to image file
            filename: Optional filename for the asset
            
        Returns:
            Asset document
        """
        url = f"https://{self.project_id}.api.sanity.io/v{self.api_version}/assets/images/{self.dataset}"
        
        with open(image_path, "rb") as f:
            files = {"file": (filename or image_path, f, "image/png")}
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                files=files
            )
            response.raise_for_status()
            
        return response.json().get("document", {})
