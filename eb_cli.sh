# Initial setup
eb init -p python-3.6 IndiePullList --region us-east-1
eb create production --instance_profile IndiePullListFlaskApp --cfg DefaultProductionConfiguration
eb open production
# Pushing changes
eb deploy production
