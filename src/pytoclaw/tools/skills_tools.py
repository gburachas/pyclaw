"""Skills tools — find and install skills from registries."""

from __future__ import annotations

import logging
from typing import Any

from pytoclaw.models import ToolResult
from pytoclaw.protocols import Tool

logger = logging.getLogger(__name__)


class FindSkillsTool(Tool):
    """Search for skills across configured registries."""

    def __init__(self) -> None:
        self._registry_manager: Any = None

    def name(self) -> str:
        return "find_skills"

    def description(self) -> str:
        return "Search for available skills to install. Returns matching skills with descriptions."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (1-20, default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def set_registry_manager(self, manager: Any) -> None:
        self._registry_manager = manager

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        query = args.get("query", "").strip()
        if not query:
            return ToolResult.error("Search query is required")

        limit = min(max(args.get("limit", 5), 1), 20)

        if self._registry_manager is None:
            return ToolResult.error("No skill registries configured")

        try:
            results = await self._registry_manager.search_all(query, limit)
            if not results:
                return ToolResult.success(f"No skills found for '{query}'")

            lines = []
            for r in results:
                lines.append(
                    f"- {r['display_name']} ({r['slug']})\n"
                    f"  {r['summary']}\n"
                    f"  Version: {r['version']} | Registry: {r['registry']}\n"
                    f"  Install: install_skill(slug=\"{r['slug']}\", "
                    f"registry=\"{r['registry']}\")"
                )
            return ToolResult.success("\n\n".join(lines))
        except Exception as e:
            return ToolResult.error(f"Search failed: {e}")


class InstallSkillTool(Tool):
    """Install a skill from a registry."""

    def __init__(self, workspace: str = ""):
        self._workspace = workspace
        self._registry_manager: Any = None

    def name(self) -> str:
        return "install_skill"

    def description(self) -> str:
        return "Install a skill from a registry into the workspace."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Skill identifier"},
                "registry": {"type": "string", "description": "Registry name"},
                "version": {
                    "type": "string",
                    "description": "Specific version (optional, latest if omitted)",
                },
                "force": {
                    "type": "boolean",
                    "description": "Reinstall if already exists",
                    "default": False,
                },
            },
            "required": ["slug", "registry"],
        }

    def set_registry_manager(self, manager: Any) -> None:
        self._registry_manager = manager

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        slug = args.get("slug", "").strip()
        registry = args.get("registry", "").strip()
        version = args.get("version", "")
        force = args.get("force", False)

        if not slug or not registry:
            return ToolResult.error("Both slug and registry are required")

        if self._registry_manager is None:
            return ToolResult.error("No skill registries configured")

        try:
            from pathlib import Path

            target_dir = Path(self._workspace) / "skills" / slug
            if target_dir.exists() and not force:
                return ToolResult.error(
                    f"Skill '{slug}' is already installed. Use force=true to reinstall."
                )

            reg = self._registry_manager.get_registry(registry)
            if reg is None:
                return ToolResult.error(f"Registry '{registry}' not found")

            # Check for malware
            meta = await reg.get_skill_meta(slug)
            if meta and meta.get("is_malware_blocked"):
                return ToolResult.error(
                    f"Skill '{slug}' has been flagged as malware and cannot be installed."
                )

            result = await reg.download_and_install(slug, version, str(target_dir))

            if result.get("is_suspicious"):
                logger.warning("Skill '%s' has been flagged as suspicious", slug)

            # Write origin metadata
            import json

            origin = {
                "slug": slug,
                "registry": registry,
                "version": result.get("version", version),
            }
            origin_path = target_dir / ".skill-origin.json"
            origin_path.write_text(json.dumps(origin, indent=2))

            return ToolResult.success(
                f"Skill '{slug}' v{result.get('version', '?')} installed successfully."
            )
        except Exception as e:
            return ToolResult.error(f"Installation failed: {e}")
