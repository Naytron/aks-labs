using './main.bicep'

param prefix = 'replace'
param location = 'eastus2'
param nodeVmSize = 'Standard_D4ds_v6'
param expiration = '2099-12-31'
param deployerObjectId = '00000000-0000-0000-0000-000000000000'
param budgetAmount = 100
param apiServerAuthorizedIpRanges = []
param systemNodeCount = 1
