# Responsibility matrix

| Area | Kubecrate maintainers | Template maintainers | Cluster owners | Application owners |
| --- | --- | --- | --- | --- |
| Vanilla composition | Own stable path, release notes, compatibility, and upstream validation | Link to the stable path without copying implementation | Choose which exact tag to consume | Rely on the provided platform contract |
| Template repository | Review minimal structure and docs for consumer safety | Own template files, examples, and static validation | Copy once into a private repository and customize placeholders | Use the private-services path for workloads |
| Consumer private repository | Do not own private identity or secrets | Do not receive automatic updates after creation | Own repo visibility, branch policy, cluster identity, Git credentials, and bootstrap | Own application manifests, domains, and service configuration |
| Flux bootstrap-generated files | Define upstream expectations only | Document generated vs hand-maintained boundaries | Own bootstrap execution and review generated output | Avoid editing generated bootstrap files for app changes |
| Git credentials and secrets | Do not receive consumer credentials | Do not include credentials in examples | Own deploy keys, tokens, kubeconfigs, and secret-manager wiring | Own application secret declarations and rotation needs |
| Kubecrate upgrades | Publish exact SemVer releases and compatibility notes after approval | Keep examples current for new template users | Adopt upgrades through private PRs and rollback by exact tag | Test application compatibility before rollout |
| Private services | May ship generic validation fixtures upstream | Provide only tiny placeholders | Own ordering and reconciliation in their private repo | Own code, manifests, operational checks, and data |
| Decommissioning | Document upstream cleanup expectations | Document safe order | Own cluster and repo retirement decisions | Own application data export and shutdown |

## Ownership principles

- Upstream Kubecrate is a versioned distribution, not a place for user-specific private configuration.
- The template is a starting point, not a managed update channel.
- The private consumer repository is the Flux root for that cluster.
- Application services belong to the application owner unless they are generic Kubecrate validation fixtures.
