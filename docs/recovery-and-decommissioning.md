# Recovery and decommissioning

## Recover failed reconciliation

Start with read-only status checks:

```sh
kubectl config current-context
flux get sources git -A
flux get kustomizations -A
kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A
```

Common failure boundaries:

- private repository authentication failed
- Kubecrate tag does not exist or is not accessible
- `kubecrate-vanilla` failed before private services started
- private services failed after Vanilla became ready
- application Secret or domain configuration is missing from the consumer repository

Fix the smallest owned boundary. If `kubecrate-upstream` or Vanilla itself fails for a released tag, open an upstream Kubecrate issue or PR with evidence. If `private-services` fails, keep the fix in your private repository.

## Suspend or pause private services

Use Flux's official suspend/resume commands for temporary investigation:

```sh
flux suspend kustomization private-services -n flux-system
flux resume kustomization private-services -n flux-system
```

Do not delete shared platform services merely to debug one private workload.

## Decommission safely

1. Confirm the target Kubernetes context.
2. Export any business data using application-owned procedures.
3. Suspend private services first if needed.
4. Remove or stop reconciling consumer-owned application manifests.
5. Follow Flux's official uninstall/decommission documentation for the cluster.
6. Delete GitHub deploy keys or tokens no longer needed.
7. Archive or delete the private repository only after cluster reconciliation has stopped.

This template does not authorize destructive cluster deletion. Treat decommissioning as a cluster-owner operation with an explicit plan and rollback point.
