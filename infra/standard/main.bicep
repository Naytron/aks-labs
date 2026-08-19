targetScope = 'subscription'

@description('Three to eight lowercase letters or digits. Use a new prefix after final Key Vault cleanup.')
@minLength(3)
@maxLength(8)
param prefix string

@description('Azure region used for all lab resources.')
param location string

@description('Four-vCPU-or-larger D-series VM size validated by preflight.')
param nodeVmSize string

@description('ISO date used by cleanup and cost governance, for example 2026-08-20.')
param expiration string

@description('Object ID of the interactive learner deploying the dedicated lab.')
param deployerObjectId string

@description('Maximum monthly budget for this lab resource group in USD.')
@minValue(20)
@maxValue(500)
param budgetAmount int = 100

@description('Optional API server source CIDRs, such as 203.0.113.10/32. Empty is convenient but not a production default.')
param apiServerAuthorizedIpRanges array = []

@description('Lab-only default is one system node. Use two or more for production.')
@minValue(1)
@maxValue(2)
param systemNodeCount int = 1

@description('Common governance tags.')
param tags object = {}

var resourceGroupName = 'rg-${prefix}-aks-labs'
var requiredTags = {
  'aks-course': 'level400'
  environment: 'lab'
  expiration: expiration
  owner: prefix
}
var allTags = union(tags, requiredTags)

resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: allTags
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
    name: '${prefix}-monthly-budget'
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
  name: 'aks-standard-platform'
  params: {
    apiServerAuthorizedIpRanges: apiServerAuthorizedIpRanges
    deployerObjectId: deployerObjectId
    location: location
    nodeVmSize: nodeVmSize
    prefix: prefix
    systemNodeCount: systemNodeCount
    tags: allTags
  }
}

output resourceGroupName string = resourceGroup.name
output clusterName string = platform.outputs.clusterName
output registryName string = platform.outputs.registryName
output keyVaultName string = platform.outputs.keyVaultName
output workloadIdentityClientId string = platform.outputs.workloadIdentityClientId
output azureMonitorWorkspaceResourceId string = platform.outputs.azureMonitorWorkspaceResourceId
output tenantId string = tenant().tenantId
