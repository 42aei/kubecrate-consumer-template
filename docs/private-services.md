# Add private application services

Private application services are workloads and configuration that belong to your private consumer repository, not to upstream Kubecrate.

The template reconciles them through `clusters/<cluster>/entrypoint/private-services/private-services-kustomization.yaml`. That Flux Kustomization depends on `kubecrate-vanilla`, so your services start after the shared Vanilla platform baseline is available.

## Add a service

1. Use one folder per app under `clusters/<cluster>/entrypoint/private-services/apps/`. Copy or delete `apps/example-app/`, the podinfo Deployment and Service example.
2. Reference each app folder from `apps/kustomization.yaml`.
3. Keep namespaces, names, domains, and secret references unique to this consumer repository.
4. Run the [render check](../README.md#validate-before-bootstrap-or-pr-review).
5. Open a private repository PR and review the rendered diff before merging.

The `private-services` Flux Kustomization has `wait: true` and `timeout: 5m0s`, so Flux waits for the app to become healthy and reports the Kustomization failed if it does not (for example, an image that cannot be pulled).

## Rules

- Do not edit Kubecrate upstream files in this repository.
- Do not copy `platform-services/` or `application-services/` from Kubecrate into the consumer repository.
- Do not change another consumer's repository to add or update this service.
- Do not commit credentials or raw Secret values.
- Keep private service reconciliation sourced from the private Flux root, not from `flux-system-sync`.
