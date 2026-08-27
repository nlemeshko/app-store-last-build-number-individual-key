#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


MARKETING_VERSION_PATTERN = re.compile(r"^\s*MARKETING_VERSION\s*=\s*(.+?)\s*$")


def find_project(explicit_project):
    if explicit_project:
        project = Path(explicit_project)
        if not project.is_dir() or project.suffix != ".xcodeproj":
            raise ValueError(f"Xcode project not found: {project}")
        return project

    projects = sorted(Path.cwd().glob("*.xcodeproj"))
    if len(projects) == 1:
        return projects[0]
    if not projects:
        raise ValueError(
            "No .xcodeproj found in the repository root. Pass project_path explicitly."
        )
    names = ", ".join(str(project) for project in projects)
    raise ValueError(
        f"Multiple .xcodeproj files found ({names}). Pass project_path explicitly."
    )


def parse_marketing_version(build_settings):
    versions = {
        match.group(1).strip()
        for line in build_settings.splitlines()
        if (match := MARKETING_VERSION_PATTERN.match(line))
    }
    if not versions:
        raise ValueError("MARKETING_VERSION was not found in xcodebuild output")
    if len(versions) != 1:
        raise ValueError(
            "Conflicting MARKETING_VERSION values returned by xcodebuild: "
            + ", ".join(sorted(versions))
        )

    version = versions.pop()
    if "$" in version:
        raise ValueError(f"MARKETING_VERSION was not fully resolved: {version}")
    return version


def load_project_objects(project):
    project_file = project / "project.pbxproj"
    result = subprocess.run(
        ["plutil", "-convert", "json", "-o", "-", str(project_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Unable to read {project_file} with plutil.\n{details}")

    try:
        return json.loads(result.stdout)["objects"]
    except (json.JSONDecodeError, KeyError) as error:
        raise RuntimeError(f"Unable to parse {project_file}: {error}") from error


def resolve_direct_project_version(objects, target, configuration):
    targets = [
        item
        for item in objects.values()
        if item.get("isa") == "PBXNativeTarget" and item.get("name") == target
    ]
    if not targets:
        raise ValueError(f"Xcode target not found: {target}")
    if len(targets) != 1:
        raise ValueError(f"Multiple Xcode targets named '{target}' were found")

    configuration_list_id = targets[0].get("buildConfigurationList")
    configuration_list = objects.get(configuration_list_id, {})
    configuration_ids = configuration_list.get("buildConfigurations", [])
    configurations = [
        objects[item_id]
        for item_id in configuration_ids
        if item_id in objects and objects[item_id].get("name") == configuration
    ]
    if not configurations:
        raise ValueError(
            f"Configuration '{configuration}' was not found for target '{target}'"
        )
    if len(configurations) != 1:
        raise ValueError(
            f"Multiple '{configuration}' configurations were found for target '{target}'"
        )

    version = configurations[0].get("buildSettings", {}).get("MARKETING_VERSION")
    if version is None or "$" in str(version):
        return None
    return str(version)


def resolve_with_xcodebuild(project, target, configuration):
    command = [
        "xcodebuild",
        "-project",
        str(project),
        "-target",
        target,
        "-configuration",
        configuration,
        "-sdk",
        "iphoneos",
        "-showBuildSettings",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            "xcodebuild failed while resolving MARKETING_VERSION for target "
            f"'{target}' ({configuration}).\n{details}"
        )
    return parse_marketing_version(result.stdout)


def resolve_version(project, target, configuration):
    objects = load_project_objects(project)
    version = resolve_direct_project_version(objects, target, configuration)
    if version is not None:
        return version

    # MARKETING_VERSION can be inherited from an xcconfig. Ask Xcode to resolve
    # the complete build settings only when the target has no direct value.
    return resolve_with_xcodebuild(project, target, configuration)


def main():
    parser = argparse.ArgumentParser(
        description="Resolve MARKETING_VERSION for one Xcode target."
    )
    parser.add_argument("--target", required=True, help="Xcode target name")
    parser.add_argument("--project", help="Path to the .xcodeproj")
    parser.add_argument("--configuration", default="Release")
    args = parser.parse_args()

    try:
        project = find_project(args.project)
        version = resolve_version(project, args.target, args.configuration)
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
