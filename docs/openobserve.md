# OpenObserve backend

One self-hosted OpenObserve OSS instance. Telemetry is kept in S3-compatible object storage, metadata in a CloudNativePG Postgres cluster with Barman Cloud backups, and every credential is delivered by External Secrets Operator from OpenBao. This binding is optional and is not enabled in `clusters/example-cluster/`. It covers the backend only; collectors are a separate binding.

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

## Prerequisites

| Prerequisite | Who does it |
| --- | --- |
| The CloudNativePG operator and the Barman Cloud plugin, reconciled by a Flux Kustomization named `cnpg`. This template does not ship them. | Consumer repository maintainer, or the platform. |
| External Secrets Operator connected to OpenBao through `optional/openbao-eso/`, with the Flux Kustomization named `eso-openbao`; see [bootstrap](bootstrap.md#connect-external-secrets-operator-to-openbao-bedrock-tenants). | Consumer repository maintainer. |
| A default storage class, or a named one. Without a default, set `persistence.storageClass` in `backend/helm-release.yaml` and `storage.storageClass` in `backend/cluster.yaml`. | Consumer repository maintainer. |
| Two S3-compatible buckets (telemetry and backups) with credentials, and the three OpenBao entries below. The template creates none of them. | Cluster owner. |

## Enable OpenObserve

1. Copy `optional/openobserve/` to `clusters/<cluster>/entrypoint/private-services/openobserve/`. The Kustomization path requires exactly this location.
2. Replace the placeholders in the copied files (table below). This check should print nothing afterwards:

   ```sh
   grep -rn REPLACE_WITH clusters/<cluster>/entrypoint/private-services/openobserve
   ```

3. Add the Kustomization file under `resources` in the root `clusters/<cluster>/entrypoint/kustomization.yaml`:

   ```yaml
   resources:
     - private-services/openobserve/openobserve-kustomization.yaml
   ```

   Do not list `backend/` there; the Flux Kustomization references that path.
4. Write the three OpenBao entries (below) before the Kustomization reconciles.
5. Run the [render check](../README.md#validate-before-bootstrap-or-pr-review) and open a private repository PR.

## Placeholders

| Placeholder | Value | Files |
| --- | --- | --- |
| `REPLACE_WITH_CLUSTER` | The cluster (tenant) ID used in the OpenBao paths and the repository path. | `openobserve-kustomization.yaml`, the three `externalsecret-*.yaml` |
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

## Verify

After Flux reconciles, check on the cluster:

- Kustomization `openobserve`: `Ready=True`.
- The three ExternalSecrets in namespace `openobserve`: `SecretSynced`.
- CloudNativePG Cluster `openobserve-meta`: healthy, and the first Backup `Completed`.
- HelmRelease `openobserve`: `Ready=True`, and the StatefulSet pod `Running`.

The render check in the README only proves the manifests render; it does not prove reconciliation on a cluster.
