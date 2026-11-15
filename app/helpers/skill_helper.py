import os

import yaml


def get_skill_details(skill_path):
    """Get the details of a skill from its SKILL.md file."""
    if os.path.exists(skill_path):
        with open(skill_path, "r") as skill_file:
            skill_file_content = skill_file.read()
        skill_content = skill_file_content.split("---")
        skill_context = yaml.safe_load(skill_content[1])
        skill_context["description"] = skill_content[2]

        return 0, skill_context
    else:
        raise RuntimeError(f"Skill file for {skill_path} not found")
