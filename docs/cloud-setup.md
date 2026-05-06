# Cloud Setup Notes

## Azure Container Apps

1. Create a resource group in Azure.
2. Create a GitHub repository and push this project.
3. Enable GitHub Container Registry package writes for the repository.
4. After the first image publish, make the GHCR packages public or add registry credentials to the Azure template.
5. Add these GitHub secrets:

- `AZURE_CREDENTIALS`: JSON credentials for a service principal.
- `AZURE_RESOURCE_GROUP`: target resource group name.
- `TOKEN_SECRET`: long random string for token signing.
- `INTERNAL_API_KEY`: long random string for service-to-service writes.
- `SNYK_TOKEN`: optional free Snyk token for DevSecOps scanning.

On push to `main`, the workflow tests, scans, builds, publishes images, and deploys the Bicep template.

## Free-Tier Controls

- Azure Container Apps template uses `minReplicas: 0` and `maxReplicas: 1`.
- Log retention is set to 30 days.
- No managed database is provisioned in this prototype.
- Each container requests only `0.25` CPU and `0.5Gi` memory.

## Production Improvements

For a real deployment, replace in-memory state with managed databases, use managed identity for service access, terminate all traffic through an API gateway, and use an identity platform such as Azure AD B2C or Auth0.
