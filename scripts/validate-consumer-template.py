#!/usr/bin/env python3
"""Static validation for kubecrate-consumer-template repositories.

The checks are intentionally conservative and local-only. They do not contact a
cluster or GitHub; live bootstrap remains an explicit operator action.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    raise

SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
FLOATING_RE = re.compile(r"^(main|master|HEAD|latest|stable|v\d+|v\d+\.\d+)$")
PLACEHOLDER_TAG = "REPLACE_WITH_KUBECRATE_SEMVER_TAG"
SECRET_WORDS = ("password", "passwd", "token", "secret", "private_key", "identity")
ALLOWED_SECRET_PATH_PARTS = {"private-services", "private-service", "private-services.md"}


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_yaml_files(root: Path):
    for suffix in ("*.yaml", "*.yml"):
        yield from root.rglob(suffix)


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def validate_git_repositories(root: Path, errors: list[str]) -> list[tuple[Path, str]]:
    kubecrate_sources: list[tuple[Path, str]] = []
    for path in iter_yaml_files(root):
        doc = load_yaml(path)
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") != "GitRepository":
            continue
        spec = doc.get("spec") or {}
        url = spec.get("url")
        ref = spec.get("ref") or {}
        name = (doc.get("metadata") or {}).get("name")
        if url == "https://github.com/42aei/kubecrate.git":
            tag = ref.get("tag")
            kubecrate_sources.append((path, str(tag)))
            require(name == "kubecrate-upstream", errors, f"{rel(path, root)}: Kubecrate GitRepository must be named kubecrate-upstream")
            require(set(ref.keys()) == {"tag"}, errors, f"{rel(path, root)}: Kubecrate source must use only ref.tag")
            if tag != PLACEHOLDER_TAG:
                require(bool(SEMVER_RE.match(str(tag))), errors, f"{rel(path, root)}: Kubecrate tag is not exact SemVer: {tag!r}")
            require(not FLOATING_RE.match(str(tag)), errors, f"{rel(path, root)}: Kubecrate ref is floating: {tag!r}")
        else:
            for key, value in ref.items():
                require(not FLOATING_RE.match(str(value)), errors, f"{rel(path, root)}: GitRepository ref.{key} is floating: {value!r}")
    require(bool(kubecrate_sources), errors, "No Kubecrate GitRepository sources found")
    return kubecrate_sources


def validate_kustomizations(root: Path, errors: list[str]) -> None:
    vanilla_paths = []
    private_paths = []
    for path in iter_yaml_files(root):
        doc = load_yaml(path)
        if not isinstance(doc, dict) or doc.get("kind") != "Kustomization":
            continue
        spec = doc.get("spec") or {}
        name = (doc.get("metadata") or {}).get("name")
        kpath = spec.get("path")
        if name == "kubecrate-vanilla":
            vanilla_paths.append(path)
            require(kpath == "./compositions/vanilla/entrypoint", errors, f"{rel(path, root)}: Vanilla path must be ./compositions/vanilla/entrypoint")
            require((spec.get("sourceRef") or {}).get("name") == "kubecrate-upstream", errors, f"{rel(path, root)}: Vanilla must source kubecrate-upstream")
        if name == "private-services":
            private_paths.append(path)
            depends = spec.get("dependsOn") or []
            require(any(d.get("name") == "kubecrate-vanilla" for d in depends if isinstance(d, dict)), errors, f"{rel(path, root)}: private-services must depend on kubecrate-vanilla")
            require(isinstance(kpath, str) and "/private-services/" in kpath, errors, f"{rel(path, root)}: private-services path must stay under private-services")
            require((spec.get("sourceRef") or {}).get("name") == "flux-system", errors, f"{rel(path, root)}: private-services must source the official Flux bootstrap root GitRepository flux-system")
    require(bool(vanilla_paths), errors, "No kubecrate-vanilla Kustomization found")
    require(bool(private_paths), errors, "No private-services Kustomization found")


def validate_fixture_isolation(root: Path, errors: list[str]) -> None:
    fixtures = sorted((root / "fixtures").glob("consumer-*")) if (root / "fixtures").exists() else []
    require(len(fixtures) >= 2, errors, "At least two independent consumer fixtures are required")
    identities = []
    tags = []
    private_namespaces = []
    fixture_owned_terms: dict[Path, set[str]] = {}
    for fixture in fixtures:
        clusters = sorted((fixture / "clusters").iterdir()) if (fixture / "clusters").exists() else []
        require(len(clusters) == 1, errors, f"{rel(fixture, root)}: fixture must contain exactly one cluster")
        if not clusters:
            continue
        cluster = clusters[0]
        identities.append(cluster.name)
        owned_terms = {fixture.name, cluster.name}
        source = cluster / "entrypoint" / "kubecrate" / "source.yaml"
        if source.exists():
            tag = (load_yaml(source).get("spec") or {}).get("ref", {}).get("tag")
            tags.append(tag)
        ns = cluster / "entrypoint" / "private-services" / "apps" / "namespace.yaml"
        if ns.exists():
            namespace = load_yaml(ns).get("metadata", {}).get("name")
            private_namespaces.append(namespace)
            if namespace:
                owned_terms.add(str(namespace))
        for yaml_path in fixture.rglob("*.yaml"):
            doc = load_yaml(yaml_path)
            if not isinstance(doc, dict):
                continue
            metadata = doc.get("metadata") or {}
            for value in (metadata.get("name"), metadata.get("namespace")):
                if value:
                    owned_terms.add(str(value))
        shared_flux_terms = {"flux-system", "kubecrate-upstream", "kubecrate-vanilla", "private-services"}
        fixture_owned_terms[fixture] = owned_terms - shared_flux_terms
    require(len(set(identities)) == len(identities), errors, f"Fixture cluster identities must be distinct: {identities}")
    require(len(set(private_namespaces)) == len(private_namespaces), errors, f"Fixture private namespaces must be distinct: {private_namespaces}")
    require(bool(tags) and len(set(tags)) == 1, errors, f"Fixtures must share one Kubecrate tag before upgrade tests: {tags}")
    require(bool(tags) and all(SEMVER_RE.match(str(tag)) for tag in tags), errors, f"Fixture tags must be exact SemVer: {tags}")
    for fixture in fixtures:
        text = "\n".join(p.read_text(encoding="utf-8") for p in fixture.rglob("*.yaml"))
        for other in fixtures:
            if other == fixture:
                continue
            leaked_terms = sorted(term for term in fixture_owned_terms.get(other, set()) if term and term in text)
            require(not leaked_terms, errors, f"{rel(fixture, root)} leaks peer fixture identities/resources from {other.name}: {leaked_terms}")


def validate_no_obvious_credentials(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel_path = rel(path, root)
        lower_path = rel_path.lower()
        if any(part in lower_path for part in ALLOWED_SECRET_PATH_PARTS):
            continue
        lower_name = path.name.lower()
        require(not any(word in lower_name for word in SECRET_WORDS), errors, f"Suspicious credential-like filename: {rel_path}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="consumer-template repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    errors: list[str] = []
    validate_git_repositories(root, errors)
    validate_kustomizations(root, errors)
    validate_fixture_isolation(root, errors)
    validate_no_obvious_credentials(root, errors)

    if errors:
        print("consumer-template validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("consumer-template validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
