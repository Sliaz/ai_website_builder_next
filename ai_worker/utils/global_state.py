"""
Global state management for the AI website builder project.
Stores project configuration including Sanity credentials and project paths.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any


class ProjectState:
    """Global project state manager."""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._state_file: Optional[Path] = None
        self.load()
    
    def _get_state_file_path(self) -> Path:
        """
        Get the path to the state file.
        If project_path is set, save in project root.
        Otherwise, save in current working directory.
        """
        if self._state_file:
            return self._state_file
            
        project_path = self._state.get("project_path")
        if project_path:
            # Save in project root as .project_state.json (hidden file)
            state_file = Path(project_path) / ".project_state.json"
        else:
            # Fallback to current directory before project is initialized
            state_file = Path("project_state.json")
        
        return state_file
    
    def load(self) -> None:
        """Load state from file if it exists."""
        # Try project-specific location first
        fallback_file = Path("project_state.json")
        if fallback_file.exists():
            state_file = fallback_file
        else:
            state_file = self._get_state_file_path()
        
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    self._state = json.load(f)
                self._state_file = state_file
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
                self._state = {}
        else:
            self._state = {}
    
    def save(self) -> None:
        """Save state to file in the project directory."""
        state_file = self._get_state_file_path()
        
        # Ensure parent directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(state_file, "w") as f:
                json.dump(self._state, f, indent=2)
            
            # Update cached file path
            self._state_file = state_file
            
            # If we had a fallback file and now have a proper location, migrate
            fallback_file = Path("project_state.json")
            if fallback_file.exists() and state_file != fallback_file:
                try:
                    fallback_file.unlink()
                    print(f"  → Migrated state file to {state_file}")
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Error saving state file: {e}")
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value and save."""
        self._state[key] = value
        self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self._state.get(key, default)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update multiple state values and save."""
        self._state.update(data)
        self.save()
    
    def clear(self) -> None:
        """Clear all state."""
        self._state = {}
        state_file = self._get_state_file_path()
        if state_file.exists():
            state_file.unlink()
    
    # Convenience properties for common values
    @property
    def project_name(self) -> Optional[str]:
        return self.get("project_name")
    
    @property
    def project_path(self) -> Optional[str]:
        return self.get("project_path")
    
    @property
    def sanity_project_id(self) -> Optional[str]:
        return self.get("sanity_project_id")
    
    @property
    def sanity_dataset(self) -> Optional[str]:
        return self.get("sanity_dataset", "production")
    
    @property
    def sanity_token(self) -> Optional[str]:
        return self.get("sanity_token")
    
    @property
    def sanity_api_version(self) -> Optional[str]:
        return self.get("sanity_api_version", "2024-01-01")
    
    def has_sanity_config(self) -> bool:
        """Check if all required Sanity configuration is present."""
        return bool(
            self.sanity_project_id 
            and self.sanity_dataset 
            and self.sanity_token
        )


# Global singleton instance
_global_state: Optional[ProjectState] = None


def get_state() -> ProjectState:
    """Get the global state instance."""
    global _global_state
    if _global_state is None:
        _global_state = ProjectState()
    return _global_state


def set_project_config(
    project_name: str,
    project_path: str,
    sanity_project_id: str,
    sanity_dataset: str = "production",
    sanity_token: Optional[str] = None,
    sanity_api_version: str = "2024-01-01"
) -> None:
    """
    Set project configuration in global state.
    
    Args:
        project_name: Name of the project
        project_path: Absolute path to the project
        sanity_project_id: Sanity project ID
        sanity_dataset: Sanity dataset name
        sanity_token: Sanity auth token (optional, can be set later)
        sanity_api_version: Sanity API version
    """
    state = get_state()
    state.update({
        "project_name": project_name,
        "project_path": project_path,
        "sanity_project_id": sanity_project_id,
        "sanity_dataset": sanity_dataset,
        "sanity_token": sanity_token,
        "sanity_api_version": sanity_api_version,
    })
    print(f"✓ Project configuration saved: {project_name}")
