"""
Filesystem tool for MCP server.

Provides secure file system operations for local file management.
"""

from pathlib import Path
from typing import Dict, Any
from . import BaseTool

class FilesystemTool(BaseTool):
    """Local filesystem operations tool."""
    
    def __init__(self):
        super().__init__("filesystem")
        self.safe_root = Path.home()  # Restrict to user home directory
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Any:
        """Execute filesystem action."""
        if action == "read":
            return await self._read_file(parameters)
        elif action == "write":
            return await self._write_file(parameters)
        elif action == "list":
            return await self._list_directory(parameters)
        else:
            return {"error": f"Unknown filesystem action: {action}"}
    
    async def _read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents."""
        path = parameters.get("path", "")
        try:
            file_path = self._safe_path(path)
            if file_path.is_file():
                content = file_path.read_text()
                return {"content": content, "path": str(file_path)}
            else:
                return {"error": f"File not found: {path}"}
        except Exception as e:
            return {"error": f"Read error: {str(e)}"}
    
    async def _write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Write file contents."""
        path = parameters.get("path", "")
        content = parameters.get("content", "")
        try:
            file_path = self._safe_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return {"success": True, "path": str(file_path)}
        except Exception as e:
            return {"error": f"Write error: {str(e)}"}
    
    async def _list_directory(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        path = parameters.get("path", ".")
        try:
            dir_path = self._safe_path(path)
            if dir_path.is_dir():
                items = []
                for item in dir_path.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                return {"items": items, "path": str(dir_path)}
            else:
                return {"error": f"Directory not found: {path}"}
        except Exception as e:
            return {"error": f"List error: {str(e)}"}
    
    def _safe_path(self, path: str) -> Path:
        """Ensure path is within safe root directory."""
        root = self.safe_root.resolve()
        full_path = (root / path).resolve()
        # Compare path components, not string prefixes: "/home/al" must not
        # admit "/home/alice", and "../" or absolute paths must be rejected.
        if full_path != root and root not in full_path.parents:
            raise ValueError("Path outside safe root directory")
        return full_path
    
    def health_check(self) -> bool:
        """Check if filesystem tool is healthy."""
        return self.safe_root.exists() and self.safe_root.is_dir()