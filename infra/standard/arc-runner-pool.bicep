targetScope = 'resourceGroup'

@description('Existing AKS cluster name.')
param clusterName string

@description('Four-vCPU-or-larger D-series VM size validated by preflight.')
param vmSize string

@description('Maximum nodes allowed in the optional ARC runner pool.')
@minValue(2)
@maxValue(5)
param maxCount int = 3

@description('Availability zones used by the existing Standard cluster.')
param availabilityZones array = [
  '1'
  '2'
  '3'
]

resource cluster 'Microsoft.ContainerService/managedClusters@2025-10-01' existing = {
  name: clusterName
}

resource arcRunnerPool 'Microsoft.ContainerService/managedClusters/agentPools@2025-10-01' = {
  parent: cluster
  name: 'arcrunner'
  properties: {
    availabilityZones: availabilityZones
    count: 0
    enableAutoScaling: true
    enableEncryptionAtHost: false
    maxCount: maxCount
    maxPods: 30
    minCount: 0
    mode: 'User'
    nodeLabels: {
      'runner-lifecycle': 'ephemeral'
      workload: 'github-runner'
    }
    nodeTaints: [
      'workload=github-runner:NoSchedule'
    ]
    orchestratorVersion: cluster.properties.kubernetesVersion
    osDiskSizeGB: 64
    osDiskType: 'Ephemeral'
    osSKU: 'AzureLinux'
    osType: 'Linux'
    scaleDownMode: 'Delete'
    scaleSetPriority: 'Regular'
    type: 'VirtualMachineScaleSets'
    upgradeSettings: {
      drainTimeoutInMinutes: 30
      maxSurge: '50%'
      nodeSoakDurationInMinutes: 0
    }
    vmSize: vmSize
  }
}

output nodePoolName string = arcRunnerPool.name
output maximumNodeCount int = maxCount
output runnerNodeLabel string = 'workload=github-runner'
output runnerNodeTaint string = 'workload=github-runner:NoSchedule'
