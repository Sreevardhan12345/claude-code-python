import os

import yaml

from .helpers.skill_helper import safe_format


class Skill:
    def __init__(self, name: str, path: str = "", args: list[str] | None = None):
        name = name.lstrip("/")
        if args is None:
            args = []
        self.path: str = path if path else f".claude/skills/{name}/SKILL.md"
        self.isPopulated: bool = False
        self._isPrepared: bool = False
        self.args = args
        self.prepare()
        if len(args) > 0:
            self.populate(args)

        self.body = self.prompt
        self.prompt = f"Skill: {self.name} (located at {self.path})\nPaths in the instructions below are relative to that folder.\n{self.prompt}"
        self.systemPrompt = f"""
        Name: {self.name}.
        Descrption: {self.description}
        """

    def prepare(self):
        """Get the details of a skill from its SKILL.md file."""
        if not self._isPrepared and os.path.exists(self.path):
            with open(self.path, "r") as skill_file:
                skill_file_splits = skill_file.read().split("---")

            skill_header = yaml.safe_load(skill_file_splits[1])

            if "name" not in skill_header or "description" not in skill_header:
                raise RuntimeError(
                    f"Skill file for {self.path} is missing required fields"
                )

            self.name = skill_header["name"]
            self.description = skill_header["description"]
            self.context = skill_header.get("context")

            self.prompt = skill_file_splits[2]
            self._isPrepared = True

        else:
            raise RuntimeError(f"Skill file for {self.path} not found")

    def populate(self, args: list[str]):
        """Populate the skill data with the provided parameters."""
        if not self._isPrepared:
            raise RuntimeError(
                f"Skill {self.name} is not prepared. Call prepare() first."
            )
        if not self.isPopulated:
            self.prompt = safe_format(self.prompt, *args)
            self.isPopulated = True
