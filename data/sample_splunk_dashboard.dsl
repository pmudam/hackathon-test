A = data('ConsumedReadCapacityUnits', filter=filter('namespace', 'AWS/DynamoDB') and filter('stat', 'mean') and filter('TableName', 'staging-prometheus*')).sum(by=['TableName']).mean(over='10m').publish(label='A')
B = data('AccountMaxTableLevelReads', filter=filter('aws_account_id', '650040788938') and filter('stat', 'count') and filter('namespace', 'AWS/DynamoDB')).sum(over='10m').mean().publish(label='B')
detect(when(A/B * 100 > threshold(90), '2m'), off=when(A/B * 100 <= threshold(90), '5m')).publish('WARN:PIAM-PREVIEW:High DynamoDB Read Capacity')
detect(when(A/B * 100 > threshold(95), '2m'), off=when(A/B * 100 <= threshold(95), '5m')).publish('ALERT:PIAM-PREVIEW:High DynamoDB Read Capacity')
