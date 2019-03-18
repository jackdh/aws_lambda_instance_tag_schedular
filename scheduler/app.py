import datetime
import boto3

client = boto3.client('ec2')


def is_weekday():
    weekno = datetime.datetime.today().weekday()
    return weekno < 5


def lambda_handler(event, context):
    date = datetime.datetime.now()

    now = date.strftime("%H:%M")

    now = date.strftime("%H:%M")
    nowMinus1 = (date - datetime.timedelta(minutes=1)).strftime("%H:%M")
    nowMinus2 = (date - datetime.timedelta(minutes=2)).strftime("%H:%M")
    nowMinus3 = (date - datetime.timedelta(minutes=3)).strftime("%H:%M")
    nowMinus4 = (date - datetime.timedelta(minutes=4)).strftime("%H:%M")

    times = [now, nowMinus1, nowMinus2, nowMinus3, nowMinus4]

    for region in client.describe_regions()['Regions']:
        region_name = region['RegionName']
        ec2 = boto3.resource('ec2', region_name=region_name)
        rds = boto3.client('rds', region_name=region_name)

        ec2_instances_to_stop = []
        ec2_instances_to_start = []
        for instance in ec2.instances.all():
            if instance.tags is not None:
                for tag in instance.tags:
                    if tag["Key"] == "Schedule:Shutdown" and tag["Value"] in times and instance.state[
                        "Name"] == "running":
                        ec2_instances_to_stop.append(instance.id)
                    elif tag["Key"] == "Schedule:Startup" and tag["Value"] in times and instance.state[
                        "Name"] == "stopped" and not is_weekday():
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

    return {
        "statusCode": 200,
        "body": "done",
    }
