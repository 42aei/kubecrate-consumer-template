# OpenObserve

One self-hosted OpenObserve OSS instance. Telemetry is kept in S3-compatible object storage, metadata in a CloudNativePG Postgres cluster with Barman Cloud backups, and every credential is delivered by External Secrets Operator from OpenBao. This binding is optional and is not enabled in `clusters/example-cluster/`. Collectors that ship metrics, logs, events and traces to it are an optional second step, described in [Collectors](#collectors).

A single instance on node-local disk is the accepted availability trade-off. There is no HA or distributed mode, no MinIO and no SQLite metadata.

## What it deploys

| Object | Name | Purpose |
| --- | --- | --- |
| Flux Kustomization | `openobserve` | Reconciles `backend/`. Depends on `eso-openbao` and `cnpg`; `wait: true`, `timeout: 15m0s`. |
| HelmRelease | `openobserve` | Chart `openobserve-standalone` `1.1.6`, image `v1.1.2`, 10Gi PVC, 90-day retention, disk cache capped at 4096 MB, vendor telemetry off. |
| ExternalSecrets | `openobserve-s3`, `openobserve-root-user`, `openobserve-backup` | S3 keys for telemetry, root user, S3 keys for the metadata backups. |
| CloudNativePG `Cluster` | `openobserve-meta` | One Postgres instance with 5Gi storage for the OpenObserve metadata. Creates Secret `openobserve-meta-app`, whose key `uri` is the DSN. |
| Barman Cloud `ObjectStore` | `openobserve-meta-backups` | Backup and WAL destination, 14-day retention. |
| `ScheduledBackup` | `openobserve-meta-daily` | A backup every day at 02:00 (and one immediately on creation). |

The requests (250m CPU, 512Mi memory) and the memory limit (2Gi) are starting values, not measurements.

The metadata Cluster has no PodDisruptionBudget (`enablePDB: false`), so a node drain is not blocked. The database is down until its pod runs again.

## Prerequisites

| Prerequisite | Who does it |
| --- | --- |
| The CloudNativePG operator and the Barman Cloud plugin, reconciled by a Flux Kustomization named `cnpg`. This template does not ship them. | Consumer repository maintainer, or the platform. |
| External Secrets Operator connected to OpenBao through `optional/openbao-eso/`, with the Flux Kustomization named `eso-openbao`; see [bootstrap](bootstrap.md#connect-external-secrets-operator-to-openbao-bedrock-tenants). | Consumer repository maintainer. |
| cert-manager, reconciled by a Flux Kustomization named `cert-manager`. The default Vanilla composition already does this; this template does not ship it. Needed only for the OpenTelemetry Operator of the [collectors](#collectors). | Consumer repository maintainer, or the platform. |
| A default storage class, or a named one. Without a default, set `persistence.storageClass` in `backend/helm-release.yaml` and `storage.storageClass` in `backend/cluster.yaml`. | Consumer repository maintainer. |
| Two S3-compatible buckets (telemetry and backups) with credentials, and the three OpenBao entries below. The template creates none of them. | Cluster owner. |

## Enable OpenObserve

1. Copy `optional/openobserve/` to `clusters/<cluster>/entrypoint/private-services/openobserve/`. The Kustomization path requires exactly this location.
2. Replace the placeholders in the copied files (table below). This check should print nothing afterwards:

   ```sh
   grep -rn REPLACE_WITH clusters/<cluster>/entrypoint/private-services/openobserve
   ```

3. Add the Kustomization files under `resources` in the root `clusters/<cluster>/entrypoint/kustomization.yaml`, the backend first:

   ```yaml
   resources:
     - private-services/openobserve/openobserve-kustomization.yaml
     - private-services/openobserve/opentelemetry-operator-kustomization.yaml
     - private-services/openobserve/openobserve-collector-kustomization.yaml
   ```

   Do not list `backend/`, `operator/` or `collector/` there; the Flux Kustomizations reference those paths. The copy in step 1 already brings all three Kustomization files and the three folders. For the backend only, leave out the last two files and delete `operator/` and `collector/` from the copy.
4. Write the three OpenBao entries (below) before the Kustomization reconciles.
5. Run the [render check](../README.md#validate-before-bootstrap-or-pr-review) and open a private repository PR.

## Placeholders

| Placeholder | Value | Files |
| --- | --- | --- |
| `REPLACE_WITH_CLUSTER` | The cluster (tenant) ID used in the OpenBao paths and the repository path. | `openobserve-kustomization.yaml`, `opentelemetry-operator-kustomization.yaml`, `openobserve-collector-kustomization.yaml`, the `externalsecret-*.yaml` files in `backend/` and `collector/`, and `collector/helm-release.yaml` (`k8sCluster`) |
| `REPLACE_WITH_S3_ENDPOINT` | Host name of the S3-compatible endpoint, without scheme. Used for telemetry and for backups. | `backend/helm-release.yaml`, `backend/objectstore.yaml` |
| `REPLACE_WITH_S3_REGION` | Region of the buckets. | `backend/helm-release.yaml`, `backend/objectstore.yaml` |
| `REPLACE_WITH_TELEMETRY_BUCKET` | Bucket that holds the telemetry. | `backend/helm-release.yaml` |
| `REPLACE_WITH_BACKUP_BUCKET` | Bucket that holds the metadata backups; the backups go under the prefix `openobserve-meta/`. | `backend/objectstore.yaml` |

OpenObserve uses path-style S3 requests unless `ZO_S3_FEATURE_FORCE_HOSTED_STYLE` is set.

## OpenBao paths

| Path | Property | Secret | Key |
| --- | --- | --- | --- |
| `tenants/<cluster>/openobserve/s3` | `access_key_id` | `openobserve-s3` | `ZO_S3_ACCESS_KEY` |
| | `secret_access_key` | `openobserve-s3` | `ZO_S3_SECRET_KEY` |
| `tenants/<cluster>/openobserve/root-user` | `email` | `openobserve-root-user` | `ZO_ROOT_USER_EMAIL` |
| | `password` | `openobserve-root-user` | `ZO_ROOT_USER_PASSWORD` |
| | `token` | `openobserve-root-user` | `ZO_ROOT_USER_TOKEN` |
| `tenants/<cluster>/openobserve/backup-s3` | `access_key_id` | `openobserve-backup` | `ACCESS_KEY_ID` |
| | `secret_access_key` | `openobserve-backup` | `ACCESS_SECRET_KEY` |

The collectors need no new OpenBao entry: `collector/externalsecret-auth.yaml` reads `email` and `token` from the existing `tenants/<cluster>/openobserve/root-user` entry.

The credentials reach the container only through `extraEnv` `secretKeyRef` (the S3 keys, the token and the metadata DSN), never through chart `auth.*` values, which would end up in the Helm release Secret in plaintext. The root user's email and password are read from Secret `openobserve-root-user` by the chart.

## Root user rules

OpenObserve reads the root user's email, password and token only at first start. Changing them in OpenBao later does not change an existing instance. They must meet these rules, or OpenObserve fails to start or the collectors get HTTP 401:

- The email is lowercase.
- The password is 8-128 characters with a lowercase letter, an uppercase letter, a digit and a special character.
- The token is non-empty. An empty token is replaced by a random one that nothing else knows.

Source: OpenObserve `v1.1.2` `src/jobs/src/job/mod.rs:360-376,391-395` and `src/config/src/utils/password.rs:24-63`.

## Access

The UI has OpenObserve's own login and no SSO, so it must stay private. This binding ships no `HTTPRoute` and no other exposure. For private access to the Service (ports 5080 and 5081), follow the NetBird pattern in [NetBird app access](netbird-app-access.md).

## What survives losing the node or the PVC

| Survives | Does not survive |
| --- | --- |
| Telemetry already uploaded to the telemetry bucket. | Telemetry not yet uploaded from the node-local disk. |
| Metadata (users, dashboards, alerts) up to the latest Barman Cloud backup plus the WAL already archived to the backup bucket. | WAL not yet uploaded when the node is lost, and metadata changed since the last uploaded WAL. |

Restoring the metadata from a backup is a CloudNativePG recovery and is outside this binding.

## Collectors

Optional. The collectors ship node and pod metrics, Kubernetes workload state, container logs, Kubernetes events and application traces to the OpenObserve instance above. They are the upstream OpenTelemetry Operator and the upstream `openobserve-collector` chart; there is no Prometheus and no Grafana. Enable them as described in [Enable OpenObserve](#enable-openobserve): all three Kustomization files, the backend first.

| Flux Kustomization | Path | Depends on | Deploys |
| --- | --- | --- | --- |
| `opentelemetry-operator` | `operator/` | `cert-manager` | Namespace `opentelemetry-operator`, HelmRepository `open-telemetry`, HelmRelease `opentelemetry-operator` (chart `0.129.0`). |
| `openobserve-collector` | `collector/` | `openobserve`, `opentelemetry-operator` | HelmRelease `openobserve-collector` (chart `0.8.3`, from the HelmRepository `openobserve`) and ExternalSecret `openobserve-collector-auth`. |

### Components and signals

| Component | Where | What it collects |
| --- | --- | --- |
| OpenTelemetry Operator | Namespace `opentelemetry-operator`. Collector image `opentelemetry-collector-contrib` `0.163.1`; webhook certificates from cert-manager. | Nothing itself: it runs the `OpenTelemetryCollector` resources below. |
| Agent | `OpenTelemetryCollector` `openobserve-collector-agent`; the operator runs it as DaemonSet `openobserve-collector-agent-collector` in `openobserve`, one pod on every node. | Container stdout/stderr logs (`filelog` on `/var/log/pods`), node metrics (`hostmetrics`) and kubelet pod and container metrics (`kubeletstats`). |
| Gateway | `OpenTelemetryCollector` `openobserve-collector-gateway`; the operator runs it as StatefulSet `openobserve-collector-gateway-collector` in `openobserve`. | Prometheus scrapes (cAdvisor, kube-state-metrics, CoreDNS, API server, scheduler, controller manager, pods by annotation), Kubernetes events (`k8sobjects/events`, stream `k8s_events`), and the OTLP receivers for application metrics and traces. |
| kube-state-metrics | Deployment in `kube-system`. | Kubernetes workload state (deployments, pods, nodes, jobs and so on), without `secrets` and `configmaps`. |

The collection interval is 30s (the chart default).

### Resources

| Component | Requests | Limit | `memory_limiter` `limit_mib` |
| --- | --- | --- | --- |
| Agent | 50m CPU, 128Mi memory | 640Mi memory | 512 |
| Gateway | 100m CPU, 256Mi memory | 1280Mi memory | 1024 |

These are starting values, not measurements. Each memory limit is above its `limit_mib`, so the limiter refuses data before the kernel kills the pod.

### Send traces from an application

The gateway listens for OTLP inside the cluster only:

- `openobserve-collector-gateway-collector.openobserve.svc:4317` (gRPC)
- `openobserve-collector-gateway-collector.openobserve.svc:4318` (HTTP)

A minimal container entry for an application that already uses an OpenTelemetry SDK:

```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: http://openobserve-collector-gateway-collector.openobserve.svc:4318
```

The gateway accepts OTLP metrics and traces only, so an application should also set `OTEL_LOGS_EXPORTER=none`. This does not make an uninstrumented application emit traces. The application must use an OpenTelemetry SDK and be configured as above. Automatic instrumentation is turned off (`autoinstrumentation.enabled: false`) and there is no `Instrumentation` resource.

### Credential

The collectors authenticate as the root user with `Basic email:token`. ExternalSecret `openobserve-collector-auth` builds that string into Secret `openobserve-collector-auth` (key `authorization`) from the `email` and `token` of the root-user entry, and a Flux post-render patch on the HelmRelease injects it into both `OpenTelemetryCollector` resources as the env var `OPENOBSERVE_AUTH`. The rendered collector configuration holds only `${env:OPENOBSERVE_AUTH}`; no credential is in the Helm values, the Helm release Secret or the `OpenTelemetryCollector` spec. OpenObserve accepts the token only on ingestion paths (`v1.1.2` `src/api/common/src/auth/validator.rs:671-680`). The [root user rules](#root-user-rules) apply: the token must be non-empty and the email lowercase, or the collectors get HTTP 401.

### Read access

The chart's ClusterRole `openobserve-collector`, bound to ServiceAccount `openobserve-collector`, is kept as the pinned chart renders it. Cluster-wide it grants:

| API group | Resources | Verbs |
| --- | --- | --- |
| (non-resource URLs) | `/metrics`, `/metrics/cadvisor` | `get`, `list`, `watch` |
| core | `configmaps`, `endpoints`, `events`, `limitranges`, `namespaces`, `namespaces/status`, `nodes`, `nodes/spec`, `nodes/stats`, `nodes/metrics`, `nodes/proxy`, `persistentvolumes`, `persistentvolumeclaims`, `pods`, `pods/status`, `replicationcontrollers`, `replicationcontrollers/status`, `resourcequotas`, `serviceaccounts`, `services` | `get`, `list`, `watch` |
| `monitoring.coreos.com` | `servicemonitors`, `podmonitors`, `probes`, `scrapeconfigs` | `*` |
| `apps` | `daemonsets`, `deployments`, `replicasets`, `statefulsets` | `get`, `list`, `watch` |
| `extensions` | `ingresses` | `get`, `list`, `watch` |
| `batch` | `jobs`, `cronjobs` | `get`, `list`, `watch` |
| `autoscaling` | `horizontalpodautoscalers` | `get`, `list`, `watch` |
| `networking.k8s.io` | `ingresses`, `networkpolicies` | `get`, `list`, `watch` |
| `rbac.authorization.k8s.io` | `roles`, `clusterroles`, `rolebindings`, `clusterrolebindings` | `get`, `list`, `watch` |
| `apiextensions.k8s.io` | `customresourcedefinitions` | `get`, `list`, `watch` |
| `storage.k8s.io` | `storageclasses` | `get`, `list`, `watch` |
| `discovery.k8s.io` | `endpointslices` | `get`, `list`, `watch` |
| `events.k8s.io` | `events` | `get`, `list`, `watch` |

The ClusterRole has no rule on `secrets`. It does include `get` on `nodes/proxy`, which opens the kubelet API, and `get`/`list` on `pods`, which returns pod env values in plain text. kube-state-metrics has its own ClusterRole with `list` and `watch` on the resources of its `--resources` list, which omits `secrets` and `configmaps`.

The agent also mounts the node read-only: `/` (as `/hostfs`), `/var/log` and `/var/lib/docker/containers`. The chart mounts the first two writable; a post-render patch on the HelmRelease makes them read-only, and fails instead of marking the wrong mount if a chart upgrade reorders the mounts. The chart mounts `/var/lib/docker/containers` read-only itself. The agent tolerates every taint, so it also runs on control-plane nodes.

The ClusterRole is not trimmed. What leaves the cluster is bounded by the receivers: only Kubernetes events are shipped as objects (`k8sobjects/events`); the chart's other `k8sobjects` receivers are set to `null`, so no ConfigMaps, pod specs or RBAC objects are shipped.

### Restarts

The agent reads pod logs from the start of each file (`start_at: beginning`) and has no checkpoint (no storage extension). After an agent restart, lines still on disk are sent again.

### Not in this binding

- Automatic instrumentation, eBPF and `Instrumentation` resources.
- An OTLP route outside the cluster.
- cert-manager: the default Vanilla composition already reconciles it.

## Verify

After Flux reconciles, check on the cluster:

- Kustomization `openobserve`: `Ready=True`.
- The three ExternalSecrets in namespace `openobserve`: `SecretSynced`.
- CloudNativePG Cluster `openobserve-meta`: healthy, and the first Backup `Completed`.
- HelmRelease `openobserve`: `Ready=True`, and the StatefulSet pod `Running`.

For the collectors:

- Kustomizations `opentelemetry-operator` and `openobserve-collector`: `Ready=True`.
- ExternalSecret `openobserve-collector-auth`: `SecretSynced`.
- HelmReleases `opentelemetry-operator` and `openobserve-collector`: `Ready=True`.
- The agent pods `Running` on every node, the gateway pod `Running`.
- Streams for logs, metrics and `k8s_events` appear in OpenObserve.

The render check in the README only proves the manifests render; it does not prove reconciliation on a cluster.
