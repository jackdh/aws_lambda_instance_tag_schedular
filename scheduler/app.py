from datetime import datetime, timedelta
import boto3

client = boto3.client('ec2')

regions = ["eu-west-1", "eu-west-2"]

default_turnoff = "18:00"

def is_weekday():
    weekno = datetime.today().weekday()
    return weekno < 5


def lambda_handler(event, context):
    date = datetime.utcnow() + timedelta(hours=1)

    now = date.strftime("%H:%M")

    now = date.strftime("%H:%M")
    nowMinus1 = (date - timedelta(minutes=1)).strftime("%H:%M")
    nowMinus2 = (date - timedelta(minutes=2)).strftime("%H:%M")
    nowMinus3 = (date - timedelta(minutes=3)).strftime("%H:%M")
    nowMinus4 = (date - timedelta(minutes=4)).strftime("%H:%M")

    times = [now, nowMinus1, nowMinus2, nowMinus3, nowMinus4]

    for region in regions:
        region_name = region
        ec2 = boto3.resource('ec2', region_name=region_name)
        rds = boto3.client('rds', region_name=region_name)
        sm = boto3.client('sagemaker', region_name=region_name)

        ec2_instances_to_stop = []
        ec2_instances_to_start = []
        for instance in ec2.instances.all():
            if instance.tags is not None:
                for tag in instance.tags:
                    if tag["Key"] == "Schedule:Shutdown" and tag["Value"] in times and instance.state["Name"] == "running":
                        ec2_instances_to_stop.append(instance.id)
                    elif tag["Key"] == "Schedule:Startup" and tag["Value"] in times and instance.state["Name"] == "stopped" and is_weekday():
                        ec2_instances_to_start.append(instance.id)

        rds_instances_to_stop = []
        rds_instances_to_start = []
        for rds_instance in rds.describe_db_instances()["DBInstances"]:
            tags = rds.list_tags_for_resource(ResourceName=rds_instance["DBInstanceArn"])['TagList']

            for rds_tag in tags:
                if rds_tag["Key"] == "Schedule:Shutdown" and rds_tag["Value"] in times and rds_instance["DBInstanceStatus"] == "available":
                    rds.stop_db_instance(DBInstanceIdentifier=rds_instance["DBInstanceIdentifier"])
                    rds_instances_to_stop.append(rds_instance["DBInstanceIdentifier"])
                elif rds_tag["Key"] == "Schedule:Startup" and rds_tag["Value"] in times and rds_instance["DBInstanceStatus"] == "stopped" and is_weekday():
                    rds.start_db_instance(DBInstanceIdentifier=rds_instance["DBInstanceIdentifier"])
                    rds_instances_to_start.append(rds_instance["DBInstanceIdentifier"])

        sm_instances_to_stop = []
        sm_instances_to_start = []
        notebooks = sm.list_notebook_instances()
        for notebook in notebooks['NotebookInstances']:
            tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])
            for sm_tag in tags["Tags"]:
                if sm_tag["Key"] == "Schedule:Shutdown" and sm_tag["Value"] in times and notebook["NotebookInstanceStatus"] == "InService":
                    sm.stop_notebook_instance(NotebookInstanceName=notebook["NotebookInstanceName"])

                    sm_instances_to_stop.append(notebook["NotebookInstanceName"])
                elif sm_tag["Key"] == "Schedule:Startup" and sm_tag["Value"] in times and notebook["NotebookInstanceStatus"] == "Stopped" and is_weekday():
                    sm.start_notebook_instance()(NotebookInstanceName=notebook["NotebookInstanceName"])
                    sm_instances_to_start.append(notebook["NotebookInstanceName"])


        if ec2_instances_to_stop:

            print(f"Stopping ec2:{ec2_instances_to_stop}")
            client_regional = boto3.client('ec2', region_name=region_name)
            client_regional.stop_instances(InstanceIds=ec2_instances_to_stop)
        if ec2_instances_to_start:
            client_regional = boto3.client('ec2', region_name=region_name)
            print(f"Starting ec2:{ec2_instances_to_start}")
            client_regional.start_instances(InstanceIds=ec2_instances_to_start)

        if rds_instances_to_start:
            print(f"Starting rds:{rds_instances_to_start}")
        if rds_instances_to_stop:
            print(f"Stopping rds:{rds_instances_to_stop}")

        if sm_instances_to_start:
            print(f"Starting sm:{sm_instances_to_start}")
        if sm_instances_to_stop:
            print(f"Stopping sm:{sm_instances_to_stop}")

    return {
        "statusCode": 200,
        "body": "done",
    }
