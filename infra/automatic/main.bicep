targetScope = 'subscription'

@description('Three to eight lowercase letters or digits.')
@minLength(3)
@maxLength(8)
param prefix string

@description('Azure region used for the short-lived comparison cluster.')
param location string

@description('Four-vCPU-or-larger D-series VM size validated by preflight.')
param nodeVmSize string

@description('ISO cleanup date.')
param expiration string

@description('Object ID of the interactive learner deploying the dedicated lab.')
param deployerObjectId string

@description('Short-lived resource-group budget.')
@minValue(10)
@maxValue(200)
param budgetAmount int = 30

var resourceGroupName = 'rg-${prefix}-automatic'
var tags = {
  'aks-course': 'level400'
  environment: 'lab'
  expiration: expiration
  owner: prefix
  purpose: 'automatic-comparison'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module budget 'br/public:avm/res/consumption/budget/rg-scope:0.1.0' = {
  scope: resourceGroup
  name: 'cost-budget'
  params: {
    amount: budgetAmount
    contactRoles: [
      'Owner'
    ]
    enableTelemetry: false
    name: '${prefix}-automatic-budget'
    thresholds: [
      50
      75
      90
      100
    ]
  }
}

module platform 'platform.bicep' = {
  scope: resourceGroup
  name: 'aks-automatic-platform'
  params: {
    deployerObjectId: deployerObjectId
    location: location
    nodeVmSize: nodeVmSize
    prefix: prefix
    tags: tags
  }
}

output resourceGroupName string = resourceGroup.name
output clusterName string = platform.outputs.clusterName
output registryName string = platform.outputs.registryName
