# NetBird app access

Give an app NetBird access with only its own manifests plus a `NetworkResource` for private access or an `HTTPRoute` for public access. This binding is optional, is not enabled in `clusters/example-cluster/`, and is only for Bedrock tenant clusters. Read the [Kubecrate operator contract](https://github.com/42aei/kubecrate/blob/v0.5.0/docs/netbird-operator.md).

## Placeholders

| Placeholder | Value | Where it comes from |
| --- | --- | --- |
| `REPLACE_WITH_CLUSTER` | Bedrock tenant ID; also the operator's `cluster.name`. The group `bedrock-<tenant>-apps` and OpenBao path `tenants/<tenant>/netbird-operator` follow from it. | Bedrock tenant configuration, `tenants/<tenant>.yaml`. |
| `REPLACE_WITH_PRIVATE_DOMAIN` | Private domain. | The `app_access` block in Bedrock's `tenants/<tenant>.yaml`. |
| `REPLACE_WITH_PUBLIC_DOMAIN` | Public domain. | The same `app_access` block. |
| `REPLACE_WITH_KUBECRATE_SEMVER_TAG` | The template's exact Kubecrate tag, at least `v0.5.0` for this binding. | Choose a Kubecrate release; `v0.5.0` is the first with `platform-services/netbird-operator/base`. |

## Prerequisites

| Prerequisite | Who does it |
| --- | --- |
| Complete "Enable app access" in the [Bedrock runbook](https://github.com/42aei/bedrock/blob/main/docs/new-tenant-cluster-runbook.md#enable-app-access). | Cluster owner / Bedrock operator. |
| Enable `optional/openbao-eso/`; see [bootstrap](bootstrap.md#connect-external-secrets-operator-to-openbao-bedrock-tenants). | Consumer repository maintainer. |
| Pin the Kubecrate tag in `clusters/<cluster>/entrypoint/kubecrate/source.yaml` to at least `v0.5.0`; see [updating Kubecrate](updating-kubecrate.md). | Consumer repository maintainer. |

## Enable app access

1. Copy `optional/netbird-app-access/`, excluding `apps/`, to `clusters/<cluster>/entrypoint/platform-services/netbird/`. The Kustomization paths require exactly this location.
2. Replace the placeholders in the copied files. This check should print nothing afterwards:

   ```sh
   grep -rn REPLACE_WITH clusters/<cluster>/entrypoint/platform-services/netbird
   ```

3. Add the three Kustomization files under `resources` in the root `clusters/<cluster>/entrypoint/kustomization.yaml`:

   ```yaml
   resources:
     - platform-services/netbird/netbird-operator-kustomization.yaml
     - platform-services/netbird/netbird-api-key-kustomization.yaml
     - platform-services/netbird/netbird-app-access-kustomization.yaml
   ```

   Do not list `api-key/` or `app-access/` there; the Flux Kustomizations reference those paths.
4. Add `netbird-app-access` to `dependsOn` in `clusters/<cluster>/entrypoint/private-services/private-services-kustomization.yaml` so apps start after the router and Gateway exist:

   ```yaml
   spec:
     dependsOn:
       - name: kubecrate-vanilla
       - name: netbird-app-access
   ```

5. Copy an example app from `optional/netbird-app-access/apps/` into `clusters/<cluster>/entrypoint/private-services/apps/`, list it in that folder's `kustomization.yaml`, and replace its placeholders. Or write your own app.
6. Run the [render check](../README.md#validate-before-bootstrap-or-pr-review), open a PR, and merge.

**Order:** operator (no wait) -> API key (waits for the ExternalSecret to sync and the operator HelmRelease to be Ready) -> router and Gateway (`wait: true`). The operator pod cannot be Ready before Secret `netbird-mgmt-api-key` exists, and the Secret needs the namespace the operator base creates. If the Secret arrives late, follow [secret arrival order](https://github.com/42aei/kubecrate/blob/v0.5.0/docs/netbird-operator.md#secret-arrival-order).

## Publish an app

- **Private:** add a `NetworkResource` on the app's own Service; see [`apps/example-private/`](../optional/netbird-app-access/apps/example-private/). Reach it at `http://<service>.<namespace>.<private domain>` (plain HTTP, port 80) from a peer in the NetBird group `bedrock-<tenant>-operators`. The Service must expose port 80: the private policy allows only tcp/80. The `NetworkResource` joins `bedrock-<tenant>-apps` by name.
- **Public:** add an `HTTPRoute` with a hostname under the public domain and parent `public` in `core-netbird-operator`, on the app's own Service; see [`apps/example-public/`](../optional/netbird-app-access/apps/example-public/). NetBird Reverse Proxy serves it over HTTPS, fully public, without login.

Give each route or resource its own Service. An `HTTPRoute` takes ownership of the `NetworkResource` named after its backend Service, so two objects on one Service compete.

There is no private Gateway and no `TCPRoute` in this binding.

## Verify

```sh
flux get kustomizations
kubectl -n core-netbird-operator get helmrelease,networkrouter,gateway
```

Expect:

- Kustomizations `netbird-operator`, `netbird-api-key`, and `netbird-app-access`: `Ready=True`.
- HelmRelease `netbird-operator`: `Ready=True`.
- NetworkRouter `apps`: `Ready=True`.
- Gateway `public`: `Programmed=True`.

## Stale peers

After a routing-pod restart, have the owner remove the old, disconnected peer in the NetBird dashboard.

## Remove app access

Remove the apps' `NetworkResource` and `HTTPRoute` objects from Git first so Flux prunes them. Then remove the Gateway and NetworkRouter. Wait until the operator's custom resources, including `setupkeys.netbird.io`, have finished their finalizers (for example, `kubectl get setupkeys.netbird.io -A` shows none) before removing the `netbird-operator` Kustomization.

Keep the operator running to delete its NetBird objects. If it is removed first, the finalizers hang.

## Limits

Check the [Kubecrate operator limits](https://github.com/42aei/kubecrate/blob/v0.5.0/docs/netbird-operator.md#limits) before publishing an app.
