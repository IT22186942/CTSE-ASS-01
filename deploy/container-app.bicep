param name string
param environmentId string
param image string
param targetPort int
param external bool
param env array
param secrets array = []

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: resourceGroup().location
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: external
        targetPort: targetPort
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: secrets
    }
    template: {
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
      containers: [
        {
          name: name
          image: image
          env: env
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

