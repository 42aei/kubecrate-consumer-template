# Bootstrap a private consumer repository

This template uses the official Flux bootstrap flow. The included `scripts/bootstrap-flux.sh` file is only a small argument wrapper around `flux bootstrap github`; it is not a Kubecrate installer or custom CLI.

## Prerequisites

- a Kubernetes cluster you own
- `kubectl` pointed at that cluster
- Flux CLI installed from the official Flux documentation
- GitHub access that can create or update the private consumer repository
- this repository configured and committed with placeholders replaced
- the [render check](../README.md#validate-before-bootstrap-or-pr-review) passing locally

## Configure placeholders

Replace the example cluster path and values with your own private identity before bootstrap:

- `clusters/example-cluster/` -> `clusters/<your-cluster>/`
- `REPLACE_WITH_PRIVATE_REPO_OWNER`
- `REPLACE_WITH_PRIVATE_REPO_NAME`
- `REPLACE_WITH_KUBECRATE_SEMVER_TAG`

The Kubecrate version must be an exact immutable SemVer tag, for example `v0.3.0`. Do not use `main`, `master`, `latest`, `stable`, `v1`, or `v1.2` as the default.

## Bootstrap

Use either the official command directly:

```sh
flux bootstrap github \
  --owner <owner> \
  --repository <repo> \
  --branch main \
  --path clusters/<cluster>/entrypoint \
  --personal=false
```

or the template wrapper:

```sh
./scripts/bootstrap-flux.sh \
  --owner <owner> \
  --repository <repo> \
  --branch main \
  --path clusters/<cluster>/entrypoint
```

Flux writes bootstrap-generated files under the selected path and creates in-cluster Flux Secrets. Review and commit generated repository files intentionally. Do not copy generated private keys or Secret values out of the cluster.

## Add flux-system to the root after bootstrap

Bootstrap generates `clusters/<cluster>/entrypoint/flux-system/`, so the template does not list it. Right after bootstrap, add `- flux-system` under `resources` in `clusters/<cluster>/entrypoint/kustomization.yaml` and merge that change. Until then, Flux does not manage its own manifests.

## Git credentials and secrets

Flux bootstrap may use your GitHub token or CLI authentication to configure the repository. That token stays in your local environment and must not be committed.

For ongoing reconciliation, keep Git credentials in Flux-managed Kubernetes Secrets or GitHub deploy keys produced by the bootstrap flow. Do not commit PATs, SSH private keys, kubeconfigs, DNS credentials, or application secrets.

Application secrets belong in your chosen secret manager and are projected into the cluster through your own consumer-owned configuration. Kubecrate and this template only define the repository boundary and reconciliation structure.

## Verify reconciliation

After bootstrap, verify the target context and Flux resources before making application changes:

```sh
kubectl config current-context
flux get sources git -A
flux get kustomizations -A
```

Expected shape:

- the private Flux root reconciles from `clusters/<cluster>/entrypoint`
- `flux-system-sync` points at `https://github.com/42aei/kubecrate.git`
- `kubecrate-vanilla` reconciles `./compositions/vanilla/entrypoint` from the pinned Kubecrate tag
- `private-services` waits for `kubecrate-vanilla` before reconciling your private application services

## Generated versus hand-maintained files

Flux bootstrap-generated files are owned by the bootstrap flow and your cluster owner. Hand-maintained consumer files are owned by your repository maintainers. Keep this distinction during reviews: do not edit generated files casually, and do not hide hand-maintained application changes inside generated bootstrap output.

## Connect External Secrets Operator to OpenBao (Bedrock tenants)

For a Bedrock tenant, first run the OpenBao steps in Bedrock's `docs/new-tenant-cluster-runbook.md`. Then copy `optional/openbao-eso/` to `clusters/<cluster>/entrypoint/platform-services/`, replace `REPLACE_WITH_CLUSTER` with the tenant ID, and add `platform-services/eso-kustomization.yaml` to the root `kustomization.yaml`. Secrets live in OpenBao under `bedrock-kv/tenants/<cluster>/`; the store reads nothing else.
