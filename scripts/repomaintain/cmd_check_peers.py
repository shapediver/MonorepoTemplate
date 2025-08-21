from utils import cmd_helper, echo, run_process, LernaComponent
import json
import re
import typing as t
import semver
from dataclasses import dataclass, field
from pathlib import Path

# Type of single NPM dependency
Dependency = t.TypedDict(
    "Dependency",
    {
        "name": str,
        "version": semver.Version,
        "components": list[str],
    },
)


@dataclass
class PeerDependencyMismatch:
    """Represents a peer dependency version mismatch."""

    dependency_name: str
    dependency_version: semver.Version
    peer_name: str
    required_peer_version: str
    actual_peer_version: semver.Version
    affected_components: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        components_str = ", ".join(self.affected_components)
        return (
            f"{self.dependency_name}@{self.dependency_version} requires peer "
            f"{self.peer_name}@{self.required_peer_version}, but found "
            f"{self.peer_name}@{self.actual_peer_version} in components: {components_str}"
        )


def _extract_version_from_string(version_str: str) -> t.Optional[semver.Version]:
    """
    Extract a valid semver version from a version string.

    Args:
        version_str: Version string that may contain prefixes like ^, ~, >=, etc.

    Returns:
        Parsed semver.Version object or None if parsing fails.
    """
    # Remove common npm version prefixes and suffixes
    clean_version = re.sub(r"^[~^>=<]+", "", version_str.strip())

    # Extract only version-like patterns (digits and dots)
    version_match = re.search(r"(\d+(?:\.\d+)*(?:\.\d+)?)", clean_version)
    if not version_match:
        return None

    version_part = version_match.group(1)

    # Ensure we have at least major.minor.patch format
    parts = version_part.split(".")
    while len(parts) < 3:
        parts.append("0")

    normalized_version = ".".join(parts[:3])

    try:
        return semver.Version.parse(normalized_version)
    except ValueError:
        return None


def _read_package_dependencies(package_json_path: Path) -> dict[str, str]:
    """
    Read and parse dependencies from a package.json file.

    Args:
        package_json_path: Path to the package.json file.

    Returns:
        Dictionary of dependency name to version string.

    Raises:
        FileNotFoundError: If package.json doesn't exist.
        json.JSONDecodeError: If package.json is malformed.
    """
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            package_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Error reading {package_json_path}: {e}")

    dependencies = {}
    for dep_type in ("dependencies", "devDependencies", "peerDependencies"):
        deps = package_data.get(dep_type, {})
        if isinstance(deps, dict):
            dependencies.update(deps)

    return dependencies


def _collect_component_dependencies(
    components: t.List[LernaComponent],
) -> dict[tuple[str, str], Dependency]:
    """
    Collect all dependencies from all components.

    Args:
        components: List of Lerna components.

    Returns:
        Dictionary mapping (name, version) tuples to Dependency objects.
    """
    dependencies: dict[tuple[str, str], Dependency] = {}

    for component in components:
        package_json_path = Path(component["location"]) / "package.json"

        if not package_json_path.is_file():
            echo(
                f"Warning: package.json not found for component {component['name']}",
                lvl="wrn",
            )
            continue

        try:
            deps_dict = _read_package_dependencies(package_json_path)
        except (ValueError, FileNotFoundError) as e:
            echo(f"Error processing {component['name']}: {e}", lvl="err")
            continue

        for name, version_str in deps_dict.items():
            version = _extract_version_from_string(version_str)
            if version is None:
                echo(
                    f"Warning: Invalid semver '{version_str}' for {name} in {component['name']}",
                    lvl="wrn",
                )
                continue

            key = (name, str(version))
            dep = dependencies.setdefault(
                key,
                {"name": name, "version": version, "components": []},
            )
            dep["components"].append(component["name"])

    return dependencies


def _fetch_peer_dependencies(
    package_name: str, version: semver.Version, root: str
) -> dict[str, str]:
    """
    Fetch peer dependencies for a specific package version.

    Args:
        package_name: Name of the npm package.
        version: Version of the package.
        root: Root directory to run the command from.

    Returns:
        Dictionary of peer dependency names to version requirements.
    """
    cmd = f"npm view {package_name}@{version} peerDependencies"
    try:
        result = run_process(cmd, root, get_output=True)
        if not result or result.strip() == "":
            return {}

        return _parse_npm_object_output(result.strip())

    except Exception as e:
        echo(
            f"Error fetching peerDependencies for {package_name}@{version}: {e}",
            lvl="err",
        )
        return {}


def _parse_npm_object_output(output: str) -> dict[str, str]:
    """
    Parse npm view output that may be in JavaScript object notation or JSON format.

    Args:
        output: Raw output from npm view command.

    Returns:
        Dictionary of parsed key-value pairs.
    """
    output = output.strip()

    # Try parsing as valid JSON first
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass

    # Try simple quote replacement for JS object notation
    try:
        # Replace unquoted keys with quoted keys and single quotes with double quotes
        fixed_output = re.sub(r"(\w+):", r'"\1":', output)  # Quote unquoted keys
        fixed_output = fixed_output.replace("'", '"')  # Replace single quotes
        return json.loads(fixed_output)
    except json.JSONDecodeError:
        pass

    # Fallback: parse line by line for simple key-value output
    result = {}
    for line in output.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")

    return result


def _find_peer_dependency_mismatches(
    dependencies: dict[tuple[str, str], Dependency], root: str
) -> list[PeerDependencyMismatch]:
    """
    Find peer dependency version mismatches.

    Args:
        dependencies: Dictionary of all collected dependencies.
        root: Root directory for running npm commands.

    Returns:
        List of peer dependency mismatches.
    """
    mismatches: list[PeerDependencyMismatch] = []

    for dep in dependencies.values():
        peer_deps = _fetch_peer_dependencies(dep["name"], dep["version"], root)

        for peer_name, peer_version_requirement in peer_deps.items():
            # Find matching dependencies by name
            matching_deps = [d for d in dependencies.values() if d["name"] == peer_name]

            for matching_dep in matching_deps:
                # Check if the actual version satisfies the peer dependency requirement
                if not _version_satisfies_requirement(
                    matching_dep["version"], peer_version_requirement
                ):
                    mismatch = PeerDependencyMismatch(
                        dependency_name=dep["name"],
                        dependency_version=dep["version"],
                        peer_name=peer_name,
                        required_peer_version=peer_version_requirement,
                        actual_peer_version=matching_dep["version"],
                        affected_components=matching_dep["components"],
                    )
                    mismatches.append(mismatch)

    return mismatches


def _version_satisfies_requirement(version: semver.Version, requirement: str) -> bool:
    """
    Check if a version satisfies a version requirement.

    Supports complex npm version requirements including:
    - Wildcard: "*" (any version)
    - Simple versions: "1.0.0"
    - Caret ranges: "^1.0.0"
    - Tilde ranges: "~1.0.0"
    - Comparison operators: ">=1.0.0", "<2.0.0"
    - OR conditions: "^8.0.1 || ^9.0.0 || ^10.0.0"
    - Combined ranges: ">=1.0.0 <2.0.0"

    Args:
        version: The actual version.
        requirement: The version requirement string.

    Returns:
        True if the version satisfies the requirement, False otherwise.
    """
    try:
        # Handle OR conditions first (||)
        if "||" in requirement:
            or_conditions = [cond.strip() for cond in requirement.split("||")]
            return any(
                _version_satisfies_single_requirement(version, cond)
                for cond in or_conditions
            )

        # Handle space-separated AND conditions (e.g., ">=1.0.0 <2.0.0")
        and_conditions = requirement.strip().split()
        if len(and_conditions) > 1:
            return all(
                _version_satisfies_single_requirement(version, cond)
                for cond in and_conditions
            )

        # Single requirement
        return _version_satisfies_single_requirement(version, requirement.strip())

    except Exception:
        return True  # If comparison fails, assume it's satisfied


def _version_satisfies_single_requirement(
    version: semver.Version, requirement: str
) -> bool:
    """
    Check if a version satisfies a single version requirement (no OR/AND logic).

    Args:
        version: The actual version.
        requirement: A single version requirement (e.g., "^1.0.0", ">=2.0.0", "*").

    Returns:
        True if the version satisfies the requirement, False otherwise.
    """
    requirement = requirement.strip()

    # Handle wildcard - any version is acceptable
    if requirement == "*":
        return True

    # Handle different requirement types
    if requirement.startswith("^"):
        # Caret range: ^1.2.3 allows >=1.2.3 but <2.0.0
        return _satisfies_caret_range(version, requirement[1:])
    elif requirement.startswith("~"):
        # Tilde range: ~1.2.3 allows >=1.2.3 but <1.3.0
        return _satisfies_tilde_range(version, requirement[1:])
    elif requirement.startswith(">="):
        # Greater than or equal
        required_version = _extract_version_from_string(requirement[2:])
        return required_version is not None and version.compare(required_version) >= 0
    elif requirement.startswith("<="):
        # Less than or equal
        required_version = _extract_version_from_string(requirement[2:])
        return required_version is not None and version.compare(required_version) <= 0
    elif requirement.startswith(">"):
        # Greater than
        required_version = _extract_version_from_string(requirement[1:])
        return required_version is not None and version.compare(required_version) > 0
    elif requirement.startswith("<"):
        # Less than
        required_version = _extract_version_from_string(requirement[1:])
        return required_version is not None and version.compare(required_version) < 0
    elif requirement.startswith("="):
        # Exact match (with explicit =)
        required_version = _extract_version_from_string(requirement[1:])
        return required_version is not None and version.compare(required_version) == 0
    else:
        # Assume exact match for plain version strings
        required_version = _extract_version_from_string(requirement)
        return required_version is not None and version.compare(required_version) == 0


def _satisfies_caret_range(version: semver.Version, requirement: str) -> bool:
    """
    Check if version satisfies caret range (^).
    ^1.2.3 := >=1.2.3 <2.0.0 (compatible within major version)
    """
    required_version = _extract_version_from_string(requirement)
    if required_version is None:
        return True

    # Must be >= required version
    if version.compare(required_version) < 0:
        return False

    # Must be < next major version
    next_major = semver.Version(required_version.major + 1, 0, 0)
    return version.compare(next_major) < 0


def _satisfies_tilde_range(version: semver.Version, requirement: str) -> bool:
    """
    Check if version satisfies tilde range (~).
    ~1.2.3 := >=1.2.3 <1.3.0 (compatible within minor version)
    """
    required_version = _extract_version_from_string(requirement)
    if required_version is None:
        return True

    # Must be >= required version
    if version.compare(required_version) < 0:
        return False

    # Must be < next minor version
    next_minor = semver.Version(required_version.major, required_version.minor + 1, 0)
    return version.compare(next_minor) < 0


def run_check_peers() -> bool:
    """
    Scans all Lerna components for NPM dependencies and groups them by name and version.
    Checks for peer dependency version conflicts and reports any mismatches.
    Returns True if successful.
    """
    try:
        # Initialize repo object and search for Lerna components
        _, root, components = cmd_helper()

        # Collect all dependencies from all components
        echo("Collecting dependencies from all components...")
        dependencies = _collect_component_dependencies(components)

        if not dependencies:
            echo("No dependencies found in any components.")
            return True

        # Check for peer dependency mismatches
        echo("Checking peer dependency requirements...")
        mismatches = _find_peer_dependency_mismatches(dependencies, root)

        if mismatches:
            echo(
                f"\nWarning: Found {len(mismatches)} peer dependency mismatches",
                lvl="wrn",
            )
            for mismatch in mismatches:
                echo(f"  {mismatch}", lvl="wrn")
        else:
            echo("\nSuccess: No peer dependency conflicts found!")

        return True

    except Exception as e:
        echo(f"Error during peer dependency check: {e}", lvl="err")
        return False
