param location string = resourceGroup().location
param imagePrefix string
param imageTag string = 'latest'
@secure()
param tokenSecret string
@secure()
param internalApiKey string

var environmentName = 'smartcart-env'
var logAnalyticsName = 'smartcart-logs'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

module auth 'container-app.bicep' = {
  name: 'auth-service'
  params: {
    name: 'auth-service'
    environmentId: environment.id
    image: '${imagePrefix}/auth-service:${imageTag}'
    targetPort: 8001
    external: true
    env: [
      { name: 'PORT', value: '8001' }
      { name: 'TOKEN_SECRET', secretRef: 'token-secret' }
      { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
      { name: 'NOTIFICATION_SERVICE_URL', value: 'https://notification-service.${environment.properties.defaultDomain}' }
    ]
    secrets: [
      { name: 'token-secret', value: tokenSecret }
      { name: 'internal-api-key', value: internalApiKey }
    ]
  }
}

module catalog 'container-app.bicep' = {
  name: 'catalog-service'
  params: {
    name: 'catalog-service'
    environmentId: environment.id
    image: '${imagePrefix}/catalog-service:${imageTag}'
    targetPort: 8002
    external: true
    env: [
      { name: 'PORT', value: '8002' }
      { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
      { name: 'NOTIFICATION_SERVICE_URL', value: 'https://notification-service.${environment.properties.defaultDomain}' }
      { name: 'ADMIN_USER_ID', value: 'catalog-admin' }
    ]
    secrets: [
      { name: 'internal-api-key', value: internalApiKey }
    ]
  }
}

module notification 'container-app.bicep' = {
  name: 'notification-service'
  params: {
    name: 'notification-service'
    environmentId: environment.id
    image: '${imagePrefix}/notification-service:${imageTag}'
    targetPort: 8004
    external: true
    env: [
      { name: 'PORT', value: '8004' }
      { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
      { name: 'AUTH_SERVICE_URL', value: 'https://auth-service.${environment.properties.defaultDomain}' }
    ]
    secrets: [
      { name: 'internal-api-key', value: internalApiKey }
    ]
  }
}

module order 'container-app.bicep' = {
  name: 'order-service'
  params: {
    name: 'order-service'
    environmentId: environment.id
    image: '${imagePrefix}/order-service:${imageTag}'
    targetPort: 8003
    external: true
    env: [
      { name: 'PORT', value: '8003' }
      { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
      { name: 'AUTH_SERVICE_URL', value: 'https://auth-service.${environment.properties.defaultDomain}' }
      { name: 'CATALOG_SERVICE_URL', value: 'https://catalog-service.${environment.properties.defaultDomain}' }
      { name: 'NOTIFICATION_SERVICE_URL', value: 'https://notification-service.${environment.properties.defaultDomain}' }
    ]
    secrets: [
      { name: 'internal-api-key', value: internalApiKey }
    ]
  }
}

output authUrl string = 'https://auth-service.${environment.properties.defaultDomain}'
output catalogUrl string = 'https://catalog-service.${environment.properties.defaultDomain}'
output orderUrl string = 'https://order-service.${environment.properties.defaultDomain}'
output notificationUrl string = 'https://notification-service.${environment.properties.defaultDomain}'

