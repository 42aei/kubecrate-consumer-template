# Update Kubecrate safely

Consumer repositories subscribe to Kubecrate through an exact SemVer tag in `clusters/<cluster>/entrypoint/kubecrate/source.yaml`:

```yaml
ref:
  tag: v0.3.0
```

A merge to Kubecrate `main` must not change your cluster. You choose when to upgrade by changing the exact tag in your private repository.

## Update workflow

1. Read the Kubecrate release notes and compatibility notes.
2. Open a private repository PR that changes only the intended version first.
3. Run the [render check](../README.md#validate-before-bootstrap-or-pr-review).
4. Dry-run your cluster manifests with your normal private-repo checks.
5. Reconcile in a safe environment before production when possible.
6. Merge only after the cluster owner accepts the diff and validation evidence.

## Rollback

Rollback is the reverse version diff: restore the previous exact tag in `clusters/<cluster>/entrypoint/kubecrate/source.yaml`, run the render check, review the PR, and let Flux reconcile the previous version.

Keep a record of the prior working tag in your private release notes or PR history. Do not roll back by editing the upstream Kubecrate repository or by switching to `main`.

## Compatibility expectations

Kubecrate maintainers own release notes, deprecation notes, and stable public composition paths. Consumer owners own the decision to adopt a release and any private-service changes needed for their cluster.

Pre-1.0 releases may change faster than stable production distributions. Treat every upgrade as a reviewed private-repo PR, even when the diff is small.
