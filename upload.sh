#!/usr/bin/env bash
sam build --use-container

sam package \
    --output-template-file packaged.yaml \
    --s3-bucket streetview-waypoint-gen

sam deploy \
    --template-file packaged.yaml \
    --stack-name Instance-Scheduler \
    --capabilities CAPABILITY_IAM \
    --region eu-west-2

aws cloudformation describe-stacks \
    --stack-name Instance-Scheduler --query 'Stacks[].Outputs' \
    --region eu-west-2