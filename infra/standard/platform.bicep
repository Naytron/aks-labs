targetScope = 'resourceGroup'

@description('Short lab prefix.')
param prefix string

@description('Azure region used for all resources.')
param location string = resourceGroup().location

@description('Four-vCPU-or-larger D-series VM size validated by preflight.')
param nodeVmSize string

@description('Optional CIDRs allowed to reach the public API endpoint.')
param apiServerAuthorizedIpRanges array = []

@description('Object ID of the interactive learner deploying the dedicated lab.')
param deployerObjectId string

@description('Lab-only system node count.')
param systemNodeCount int = 1

@description('Common tags.')
param tags object

var suffix = substring(uniqueString(subscription().id, resourceGroup().id), 0, 6)
var clusterName = 'aks-${prefix}-standard'
var registryName = '${replace(prefix, '-', '')}acr${suffix}'
var keyVaultName = 'kv-${prefix}-${suffix}'
var logAnalyticsName = 'log-${prefix}-${suffix}'
var monitorWorkspaceName = 'amw-${prefix}-${suffix}'
var workloadIdentityName = 'id-${prefix}-orders'
var controlPlaneIdentityName = 'id-${prefix}-aks-control'
var virtualNetworkName = 'vnet-${prefix}-aks'
var networkContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4d97b98b-1d4f-4787-a291-c67834d212e7'
)
var monitoringDataReaderRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b0d8363b-8ddd-447d-831f-62ca05bff136'
)

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2025-05-01' = {
  name: virtualNetworkName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.40.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'nodes'
        properties: {
          addressPrefix: '10.40.0.0/22'
        }
      }
      {
        name: 'apiserver'
        properties: {
          addressPrefix: '10.40.4.0/28'
          delegations: [
            {
              name: 'aks-api-server'
              properties: {
                serviceName: 'Microsoft.ContainerService/managedClusters'
              }
            }
          ]
        }
      }
    ]
  }
}

resource nodeSubnet 'Microsoft.Network/virtualNetworks/subnets@2025-05-01' existing = {
  name: 'nodes'
  parent: virtualNetwork
}

resource apiServerSubnet 'Microsoft.Network/virtualNetworks/subnets@2025-05-01' existing = {
  name: 'apiserver'
  parent: virtualNetwork
}

module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.16.0' = {
  name: 'log-analytics'
  params: {
    dailyQuotaGb: '0.5'
    dataRetention: 30
    enableTelemetry: false
    location: location
    name: logAnalyticsName
    tags: tags
  }
}

resource azureMonitorWorkspace 'Microsoft.Monitor/accounts@2025-10-03' = {
  name: monitorWorkspaceName
  location: location
  tags: tags
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource learnerPrometheusReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(azureMonitorWorkspace.id, deployerObjectId, monitoringDataReaderRoleDefinitionId)
  scope: azureMonitorWorkspace
  properties: {
    principalId: deployerObjectId
    principalType: 'User'
    roleDefinitionId: monitoringDataReaderRoleDefinitionId
  }
}

module controlPlaneIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'aks-control-plane-identity'
  params: {
    enableTelemetry: false
    location: location
    name: controlPlaneIdentityName
    tags: tags
  }
}

resource nodeSubnetNetworkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(nodeSubnet.id, controlPlaneIdentityName, networkContributorRoleDefinitionId)
  scope: nodeSubnet
  properties: {
    principalId: controlPlaneIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: networkContributorRoleDefinitionId
  }
}

resource apiServerSubnetNetworkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(apiServerSubnet.id, controlPlaneIdentityName, networkContributorRoleDefinitionId)
  scope: apiServerSubnet
  properties: {
    principalId: controlPlaneIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: networkContributorRoleDefinitionId
  }
}

module cluster 'br/public:avm/res/container-service/managed-cluster:0.14.0' = {
  name: 'aks-standard'
  params: {
    aadProfile: {
      enableAzureRBAC: true
      managed: true
      tenantID: tenant().tenantId
    }
    agentPools: [
      {
        availabilityZones: [
          1
          2
          3
        ]
        enableAutoScaling: true
        maxCount: 3
        maxPods: 110
        minCount: 1
        mode: 'User'
        name: 'user'
        nodeLabels: {
          workload: 'general'
        }
        osDiskSizeGB: 64
        osDiskType: 'Ephemeral'
        osSKU: 'AzureLinux'
        osType: 'Linux'
        type: 'VirtualMachineScaleSets'
        upgradeSettings: {
          drainTimeoutInMinutes: 30
          maxSurge: '50%'
          nodeSoakDurationInMinutes: 0
        }
        vmSize: nodeVmSize
        vnetSubnetResourceId: nodeSubnet.id
      }
    ]
    apiServerAccessProfile: union({
      enablePrivateCluster: false
      enableVnetIntegration: true
      subnetId: apiServerSubnet.id
    }, empty(apiServerAuthorizedIpRanges) ? {} : {
      authorizedIPRanges: apiServerAuthorizedIpRanges
    })
    autoScalerProfile: {
      'balance-similar-node-groups': 'true'
      expander: 'least-waste'
      'max-graceful-termination-sec': '600'
      'scale-down-delay-after-add': '10m'
      'scale-down-unneeded-time': '10m'
      'scale-down-utilization-threshold': '0.5'
      'scan-interval': '10s'
      'skip-nodes-with-local-storage': 'false'
      'skip-nodes-with-system-pods': 'true'
    }
    autoUpgradeProfile: {
      nodeOSUpgradeChannel: 'NodeImage'
      upgradeChannel: 'stable'
    }
    azurePolicyEnabled: true
    azurePolicyVersion: 'v2'
    costAnalysisEnabled: true
    diagnosticSettings: [
      {
        logCategoriesAndGroups: [
          {
            category: 'cluster-autoscaler'
          }
          {
            category: 'kube-apiserver'
          }
          {
            category: 'kube-audit-admin'
          }
          {
            category: 'kube-controller-manager'
          }
          {
            category: 'kube-scheduler'
          }
        ]
        metricCategories: [
          {
            category: 'AllMetrics'
          }
        ]
        name: 'control-plane'
        workspaceResourceId: logAnalytics.outputs.resourceId
      }
    ]
    disableLocalAccounts: true
    dnsServiceIP: '10.0.0.10'
    enableKeyvaultSecretsProvider: true
    enableOidcIssuerProfile: true
    enableRBAC: true
    enableSecretRotation: true
    enableStorageProfileBlobCSIDriver: true
    enableStorageProfileDiskCSIDriver: true
    enableStorageProfileFileCSIDriver: true
    enableStorageProfileSnapshotController: true
    loadBalancerSku: 'standard'
    location: location
    maintenanceConfigurations: [
      {
        maintenanceWindow: {
          durationHours: 4
          schedule: {
            weekly: {
              dayOfWeek: 'Sunday'
              intervalWeeks: 1
            }
          }
          startDate: '2026-01-04'
          startTime: '02:00'
          utcOffset: '+00:00'
        }
        name: 'aksManagedAutoUpgradeSchedule'
      }
      {
        maintenanceWindow: {
          durationHours: 4
          schedule: {
            weekly: {
              dayOfWeek: 'Saturday'
              intervalWeeks: 1
            }
          }
          startDate: '2026-01-03'
          startTime: '02:00'
          utcOffset: '+00:00'
        }
        name: 'aksManagedNodeOSUpgradeSchedule'
      }
    ]
    managedIdentities: {
      userAssignedResourceIds: [
        controlPlaneIdentity.outputs.resourceId
      ]
    }
    monitoringWorkspaceResourceId: logAnalytics.outputs.resourceId
    name: clusterName
    networkDataplane: 'cilium'
    networkPlugin: 'azure'
    networkPluginMode: 'overlay'
    networkPolicy: 'cilium'
    nodeProvisioningProfile: {
      mode: 'Manual'
    }
    nodeResourceGroup: '${resourceGroup().name}-nodes'
    nodeResourceGroupProfile: {
      restrictionLevel: 'ReadOnly'
    }
    omsAgentEnabled: true
    omsAgentUseAADAuth: true
    managedOutboundIPCount: 1
    outboundType: 'loadBalancer'
    podCidr: '10.244.0.0/16'
    primaryAgentPoolProfiles: [
      {
        availabilityZones: [
          1
          2
          3
        ]
        count: systemNodeCount
        enableAutoScaling: true
        maxCount: 2
        maxPods: 110
        minCount: systemNodeCount
        mode: 'System'
        name: 'system'
        nodeTaints: [
          'CriticalAddonsOnly=true:NoSchedule'
        ]
        osDiskSizeGB: 64
        osDiskType: 'Ephemeral'
        osSKU: 'AzureLinux'
        osType: 'Linux'
        type: 'VirtualMachineScaleSets'
        upgradeSettings: {
          drainTimeoutInMinutes: 30
          maxSurge: '50%'
          nodeSoakDurationInMinutes: 0
        }
        vmSize: nodeVmSize
        vnetSubnetResourceId: nodeSubnet.id
      }
    ]
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: deployerObjectId
        principalType: 'User'
        roleDefinitionIdOrName: 'Azure Kubernetes Service RBAC Cluster Admin'
      }
    ]
    securityProfile: {
      imageCleaner: {
        enabled: true
        intervalHours: 48
      }
      workloadIdentity: {
        enabled: true
      }
    }
    serviceCidr: '10.0.0.0/16'
    skuName: 'Base'
    skuTier: 'Standard'
    supportPlan: 'KubernetesOfficial'
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
  dependsOn: [
    apiServerSubnetNetworkContributor
    nodeSubnetNetworkContributor
  ]
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

module workloadIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'orders-workload-identity'
  params: {
    enableTelemetry: false
    federatedIdentityCredentials: [
      {
        audiences: [
          'api://AzureADTokenExchange'
        ]
        issuer: cluster.outputs.oidcIssuerUrl!
        name: 'orders-api'
        subject: 'system:serviceaccount:orders:orders-api'
      }
    ]
    location: location
    name: workloadIdentityName
    tags: tags
  }
}

module keyVault 'br/public:avm/res/key-vault/vault:0.14.0' = {
  name: 'key-vault'
  params: {
    diagnosticSettings: [
      {
        name: 'audit'
        workspaceResourceId: logAnalytics.outputs.resourceId
      }
    ]
    enablePurgeProtection: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    enableTelemetry: false
    location: location
    name: keyVaultName
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: deployerObjectId
        principalType: 'User'
        roleDefinitionIdOrName: 'Key Vault Secrets Officer'
      }
      {
        principalId: workloadIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Key Vault Secrets User'
      }
    ]
    softDeleteRetentionInDays: 7
    tags: tags
  }
}

output azureMonitorWorkspaceResourceId string = azureMonitorWorkspace.id
output clusterName string = cluster.outputs.name
output clusterResourceId string = cluster.outputs.resourceId
output keyVaultName string = keyVault.outputs.name
output logAnalyticsWorkspaceResourceId string = logAnalytics.outputs.resourceId
output oidcIssuerUrl string = cluster.outputs.oidcIssuerUrl!
output registryName string = registry.outputs.name
output workloadIdentityClientId string = workloadIdentity.outputs.clientId
