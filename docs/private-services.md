# Add private application services

Private application services are workloads and configuration that belong to your private consumer repository, not to upstream Kubecrate.

The template reconciles them through `clusters/<cluster>/entrypoint/private-services/private-services-kustomization.yaml`. That Flux Kustomization depends on `kubecrate-vanilla`, so your services start after the shared Vanilla platform baseline is available.

## Add a service

1. Add manifests under `clusters/<cluster>/entrypoint/private-services/apps/`.
2. Reference them from `clusters/<cluster>/entrypoint/private-services/apps/kustomization.yaml`.
3. Keep namespaces, names, domains, and secret references unique to this consumer repository.
4. Run validation:

```sh
python3 scripts/validate-consumer-template.py .
```

5. Open a private repository PR and review the rendered diff before merging.

## Rules

- Do not edit Kubecrate upstream files in this repository.
- Do not copy `platform-services/` or `application-services/` from Kubecrate into the consumer repository.
- Do not change another consumer's repository to add or update this service.
- Do not commit credentials or raw Secret values.
- Keep private service reconciliation sourced from the private Flux root, not from `kubecrate-upstream`.

## Example

The fixture ConfigMaps under `fixtures/consumer-a/` and `fixtures/consumer-b/` demonstrate two unrelated consumers with distinct cluster names, namespaces, and private services while sharing one Kubecrate tag. They are static proof fixtures, not recommended production workloads.
