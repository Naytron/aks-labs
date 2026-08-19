targetScope = 'resourceGroup'

param prefix string
param location string = resourceGroup().location
param nodeVmSize string
param deployerObjectId string
param tags object

var suffix = substring(uniqueString(subscription().id, resourceGroup().id), 0, 6)
var clusterName = 'aks-${prefix}-automatic'
var registryName = '${replace(prefix, '-', '')}autoacr${suffix}'

module cluster 'br/public:avm/res/container-service/managed-cluster:0.14.0' = {
  name: 'aks-automatic'
  params: {
    aadProfile: {
      enableAzureRBAC: true
      managed: true
    }
    autoUpgradeProfile: {
      nodeOSUpgradeChannel: 'NodeImage'
    }
    disableLocalAccounts: true
    enableKeyvaultSecretsProvider: true
    enableOidcIssuerProfile: true
    enableSecretRotation: true
    enableStorageProfileDiskCSIDriver: true
    enableStorageProfileFileCSIDriver: true
    enableStorageProfileSnapshotController: true
    location: location
    managedIdentities: {
      systemAssigned: true
    }
    name: clusterName
    nodeProvisioningProfile: {
      mode: 'Auto'
    }
    nodeResourceGroupProfile: {
      restrictionLevel: 'ReadOnly'
    }
    outboundType: 'managedNATGateway'
    primaryAgentPoolProfiles: [
      {
        count: 1
        mode: 'System'
        name: 'systempool'
        vmSize: nodeVmSize
      }
    ]
    publicNetworkAccess: 'Enabled'
    costAnalysisEnabled: true
    roleAssignments: [
      {
        principalId: deployerObjectId
        principalType: 'User'
        roleDefinitionIdOrName: 'Azure Kubernetes Service RBAC Cluster Admin'
      }
    ]
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
    skuName: 'Automatic'
    tags: tags
    webApplicationRoutingEnabled: false
    workloadAutoScalerProfile: {
      keda: {
        enabled: true
      }
      verticalPodAutoscaler: {
        enabled: true
      }
    }
  }
}

module registry 'br/public:avm/res/container-registry/registry:0.12.0' = {
  name: 'container-registry'
  params: {
    acrAdminUserEnabled: false
    acrSku: 'Basic'
    enableTelemetry: false
    location: location
    name: registryName
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: cluster.outputs.kubeletIdentityObjectId!
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
    ]
    tags: tags
  }
}

output clusterName string = cluster.outputs.name
output registryName string = registry.outputs.name
