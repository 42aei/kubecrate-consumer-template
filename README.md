# Kubecrate consumer template

This repository is a minimal GitHub template for creating a private Flux root that consumes the public `42aei/kubecrate` Vanilla composition.

Use it when a cluster owner wants an independent private repository for cluster identity, Git credentials, domains, secrets declarations, and private application services without forking Kubecrate or using a custom Kubecrate CLI.

## What this template owns

- a consumer Flux root under `clusters/<cluster>/entrypoint/`
- a Kubecrate `GitRepository` pinned to one exact upstream SemVer tag
- a Flux `Kustomization` that reconciles Kubecrate's stable Vanilla composition from that tag
- a separate private-services path that depends on Vanilla
- small examples
- documentation for bootstrap, updates, rollback, recovery, and decommissioning

## What this template does not own

- Kubecrate platform-service implementation
- user domains, cluster names, credentials, or secrets
- release automation for Kubecrate
- live cluster bootstrap on your behalf
- automatic updates after you create a repository from the template

Template files are copied by GitHub when you create your private repository. Later changes to this template do not automatically update repositories already created from it.

## Repository layout

```text
clusters/example-cluster/entrypoint/                                    Flux root for one concrete cluster
clusters/example-cluster/entrypoint/private-services/                   Private application-service path
clusters/example-cluster/entrypoint/private-services/apps/example-app/  Example app (podinfo); copy or delete
clusters/example-cluster/entrypoint/kubecrate/                          Kubecrate source and Vanilla reconciliation
scripts/bootstrap-flux.sh                                               Thin official Flux bootstrap wrapper
.github/workflows/render.yaml                                           Render check run on every pull request
docs/                                                                   Consumer operating docs
```

## Quick start

1. Create a new private repository from this template.
2. Replace obvious placeholders in `clusters/example-cluster/`:
   - `example-cluster`
   - `REPLACE_WITH_PRIVATE_REPO_OWNER`
   - `REPLACE_WITH_PRIVATE_REPO_NAME`
   - `REPLACE_WITH_KUBECRATE_SEMVER_TAG`
3. Keep the Kubecrate version pinned to an exact tag such as `v0.3.0`. Do not use `main`, `master`, `latest`, or a floating major tag.
4. Commit the configured consumer repository.
5. Bootstrap Flux with the official Flux CLI or the thin wrapper in this template:

```sh
./scripts/bootstrap-flux.sh \
  --owner REPLACE_WITH_PRIVATE_REPO_OWNER \
  --repository REPLACE_WITH_PRIVATE_REPO_NAME \
  --branch main \
  --path clusters/example-cluster/entrypoint
```

The wrapper calls `flux bootstrap github`. Review `docs/bootstrap.md` before running it.

6. After bootstrap, pull and add `- flux-system` to `resources` in `clusters/example-cluster/entrypoint/kustomization.yaml`, then commit and push. See [Add flux-system to the root](docs/bootstrap.md#add-flux-system-to-the-root).

## Validate before bootstrap or PR review

```sh
docker run --rm -v "$PWD":/r:ro --entrypoint sh registry.k8s.io/kustomize/kustomize:v5.4.3 -c 'cd /r; rc=0; for p in $(find . -name kustomization.yaml -not -path "./.git/*" -exec dirname {} \;); do kustomize build "$p" >/dev/null || rc=1; done; exit $rc'
```

This command renders every `kustomization.yaml` in the repository with kustomize and requires Docker locally. The workflow `.github/workflows/render.yaml` runs the same command on every pull request. It does not prove bootstrap or reconciliation on a cluster.

## Documentation

- `docs/bootstrap.md` - prerequisites, bootstrap, generated files, verification, and Git credential handling
- `docs/private-services.md` - add and verify private application services
- `docs/updating-kubecrate.md` - update, rollback, and compatibility workflow
- `docs/recovery-and-decommissioning.md` - recover failed reconciliation and remove a cluster safely
- `docs/responsibility-matrix.md` - who owns which files and actions

## Safety

Do not commit credentials, kubeconfigs, domain-specific secrets, deploy keys, personal identity, or generated Flux private keys. Keep those in the cluster Secret created by Flux bootstrap or in your chosen secret manager.

Do not bootstrap a real cluster from this repository until the placeholders have been replaced and the render check passes.
