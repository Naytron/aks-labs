targetScope = 'resourceGroup'

@description('Existing AKS cluster name.')
param clusterName string

@description('Short-lived Spot node pool VM SKU. Validate regional quota first.')
param vmSize string = 'Standard_D4as_v5'

resource cluster 'Microsoft.ContainerService/managedClusters@2025-10-01' existing = {
  name: clusterName
}

resource spotPool 'Microsoft.ContainerService/managedClusters/agentPools@2025-10-01' = {
  parent: cluster
  name: 'spot'
  properties: {
    availabilityZones: [
      '1'
      '2'
      '3'
    ]
    count: 0
    enableAutoScaling: true
    enableEncryptionAtHost: false
    maxCount: 3
    maxPods: 110
    minCount: 0
    mode: 'User'
    nodeLabels: {
      'kubernetes.azure.com/scalesetpriority': 'spot'
      workload: 'interruptible'
    }
    nodeTaints: [
      'kubernetes.azure.com/scalesetpriority=spot:NoSchedule'
    ]
    orchestratorVersion: cluster.properties.kubernetesVersion
    osDiskSizeGB: 64
    osDiskType: 'Ephemeral'
    osSKU: 'AzureLinux'
    osType: 'Linux'
    scaleSetPriority: 'Spot'
    scaleSetEvictionPolicy: 'Delete'
    spotMaxPrice: -1
    type: 'VirtualMachineScaleSets'
    upgradeSettings: {
      drainTimeoutInMinutes: 30
      maxSurge: '50%'
      nodeSoakDurationInMinutes: 0
    }
    vmSize: vmSize
  }
}

output nodePoolName string = spotPool.name
