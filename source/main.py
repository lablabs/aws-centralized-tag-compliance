import os, json, boto3, botocore
from botocore.exceptions import ClientError
import urllib.request, urllib.parse
from urllib.error import HTTPError
from operator import itemgetter
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')

# Get Environment Variables
REQUIRED_TAGS_JSON = os.environ['REQUIRED_TAGS']

SLACK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
SLACK_USERNAME = os.environ['SLACK_USERNAME']
SLACK_ICON_URL = os.environ['SLACK_ICON_URL']

ENABLE_EC2_Instance = os.getenv('ENABLE_EC2_Instance', 'True')
ENABLE_S3_Bucket = os.getenv('ENABLE_S3_Bucket', 'True')
ENABLE_DynamoDB_Table = os.getenv('ENABLE_DynamoDB_Table', 'True')
ENABLE_ElastiCache_Node = os.getenv('ENABLE_ElastiCache_Node', 'True')
ENABLE_ElasticLoadBalancing_Loadbalancer = os.getenv('ENABLE_ElasticLoadBalancing_Loadbalancer', 'True')
ENABLE_RDS_Cluster = os.getenv('ENABLE_RDS_Cluster', 'True')
ENABLE_SQS_Queue = os.getenv('ENABLE_SQS_Queue', 'True')
ENABLE_ElasticSearch_Cluster = os.getenv('ENABLE_ElasticSearch_Cluster', 'True')

ENABLE_Slack_Notifications = os.getenv('ENABLE_Slack_Notifications', 'True')

REQUIRED_TAGS=json.loads(REQUIRED_TAGS_JSON)

def str2bool(v):
  return v.lower() in ("yes", "true", "True", "t", "1")

def get_ec2_instance_resources():
    resource = boto3.resource('ec2')
    instances = []

    logging.info("Getting EC2:instance resources")
    for instance in resource.instances.all():
        instances.append({ "service" : "EC2:Instance", "id" : instance.id, "tags" : instance.tags })

    return instances

def get_dynamodb_table_resources():
    dynamodb = boto3.client('dynamodb')
    dynamodb_re = boto3.resource('dynamodb')
    tables = []

    logging.info("Getting DynamoDB:Table resources")
    for table in dynamodb_re.tables.all():
        tags = []
        try:
            tags = dynamodb.list_tags_of_resource(ResourceArn=table.table_arn)['Tags']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        tables.append({ "service" : "DynamoDB:Table", "id" : table.name, "tags" : tags })
        
    return tables

def get_s3_bucket_resources():
    s3 = boto3.client('s3')
    s3_re = boto3.resource('s3')
    buckets = []

    logging.info("Getting S3:Bucket resources")
    for bucket in s3_re.buckets.all():
        tags = []
        try:
            tags = s3.get_bucket_tagging(Bucket=bucket.name)['TagSet']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        buckets.append({ "service" : "S3:Bucket", "id" : bucket.name, "tags" : tags })
        
    return buckets

def get_elasticache_node_resources():
    elasticache = boto3.client('elasticache')
    sts = boto3.client('sts')
    clusters = []

    logging.info("Getting ElastiCache:Node resources")
    arn_prefix = "arn:aws:elasticache:" + elasticache.meta.region_name + ":" + sts.get_caller_identity()["Account"] + ":cluster:"
    for cluster in elasticache.describe_cache_clusters()['CacheClusters']:
        tags = []
        try:
            tags = elasticache.list_tags_for_resource(ResourceName=arn_prefix + cluster['CacheClusterId'])['TagList']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        clusters.append({ "service" : "ElastiCache:Node", "id" : cluster['CacheClusterId'], "tags" : tags })
    
    return clusters

def get_elb_loadbalancer_resources():
    elb = boto3.client('elb')
    loadbalancers = []

    logging.info("Getting ElasticLoadBalancing:Loadbalancer resources")
    for loadbalancer in elb.describe_load_balancers()['LoadBalancerDescriptions']:
        tags = []
        try:
            tags = elb.describe_tags(LoadBalancerNames=[loadbalancer['LoadBalancerName']])['TagDescriptions'][0]['Tags']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        loadbalancers.append({ "service" : "ElasticLoadBalancing:Loadbalancer", "id" : loadbalancer['LoadBalancerName'], "tags" : tags })
    
    return loadbalancers

def get_rds_cluster_resources():
    rds = boto3.client('rds')
    clusters = []

    logging.info("Getting RDS:Cluster resources")
    for cluster in rds.describe_db_clusters()['DBClusters']:
        tags = []
        try:
            tags = rds.list_tags_for_resource(ResourceName=cluster['DBClusterArn'])['TagList']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        clusters.append({ "service" : "RDS:Cluster", "id" : cluster['DBClusterIdentifier'], "tags" : tags })
    
    return clusters

def get_sqs_queue_resources():
    sqs = boto3.client('sqs')
    queues = []

    logging.info("Getting SQS:Queue resources")
    list_queues = sqs.list_queues()
    if 'QueueUrls' in list_queues:
        for queue in list_queues['QueueUrls']:
            tags = []
            sqs_response = []
            try:
                sqs_response = sqs.list_queue_tags(QueueUrl=queue)['Tags']
            except ClientError as e:
                logging.error(("Unexpected error: %s" % e))
            # sqs.list_queue_tags reponse needs to be reformatted
            for r in sqs_response: tags.append({"Key": r, "Value": sqs_response[r]})

            queues.append({ "service" : "SQS:Queue", "id" : queue, "tags" : tags })
    else:
        queues = []

    return queues

def get_elasticsearch_cluster_resources():
    es = boto3.client('es')
    clusters = []

    logging.info("Getting ElasticSearch:Cluster resources")
    for cluster in es.list_domain_names()['DomainNames']:
        tags = []
        try:
            tags = es.list_tags(ARN=es.describe_elasticsearch_domain(DomainName=cluster['DomainName'])['DomainStatus']['ARN'])['TagList']
        except ClientError as e:
            logging.error(("Unexpected error: %s" % e))
        clusters.append({ "service" : "ElasticSearch:Cluster", "id" : cluster['DomainName'], "tags" : tags })
    
    return clusters

def verify_tags_on_resource(resource,required_tags):
    """
    Verifies whether a resource is compliant with required tags.
    Input:
    resource - Information about the resource which should be verified. Example: {"service": "ec2:instance", "id": "i-1111", "tags": [{"Key": "environment", "Value": "prod"}, {"Key": "Project", "Value": "p1"}]}
    required_tags - Tags which are required for the compliance. Example: [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":["prod", "dev"]}]
    Return:
    True - If the resource is compliant
    False
    """
    compliant_status = True
    compliant_reasons = []

    for required_tag in required_tags:
        if check_if_tag_exists(resource['tags'],required_tag['key']):
            if not check_if_tag_is_compliant(resource['tags'],required_tag['key'],required_tag['values']):
                compliant_status = False
                logging.info(resource['service'] + "|" + resource['id'] + "| tag " + required_tag['key'] + " is not compliant with " + str(required_tag['values']))
                compliant_reasons.append("tag '" + required_tag['key'] + "' is not compliant with '" + ",".join(required_tag['values']) + "'")
        else:
            compliant_status = False
            logging.info(resource['service'] + "|" + resource['id'] + "| tag " + required_tag['key'] + " does not exist")
            compliant_reasons.append("tag '" + required_tag['key'] + "' does not exist")
    resource['compliant_reasons'] = compliant_reasons
    return compliant_status

def check_if_tag_exists(resource_tags,required_tag_key):
    """
    Input:
    resource_tags - A list of dictionaries which contains AWS tags. Example: [{"Key": "Tag1Key", "Value": "Tag1Value"}, {"Key": "Tag2Key", "Value": "Tag2Value"}]
    required_tag_key - An AWS tag key in string. Example: "Tag1Key"
    Return:
    True - If required_tag_key can be found in resource_tags
    False
    """
    if resource_tags is None or not required_tag_key in map(itemgetter('Key'), resource_tags):
        return False
    else:
        return True

def check_if_tag_is_compliant(resource_tags,required_tag_key,required_tag_values):
    """
    Input:
    resource_tags - A list of dictionaries which contains AWS tags. Example: [{"Key": "Tag1Key", "Value": "Tag1Value"}, {"Key": "Tag2Key", "Value": "Tag2Value"}]
    required_tag_key - An AWS tag key as a string. Example: "Tag1Key"
    required_tag_values - A list of strings which are AWS tag values. Example: ["Tag1Value","Tag2Value"]
    Return:
    True - If required_tag_key in resource_tags has a value which can be found in required_tag_values or in case there is "*" in required_tag_values list.
    False
    """
    if resource_tags is None:
        return False
    else:
        for t in resource_tags:
            if t["Key"] == required_tag_key:
                if t["Value"] in required_tag_values or "*" in required_tag_values:
                    return True
                else:
                    return False
    return False

def notify_slack(resource):
    """
    Sends a notification to Slack.
    Input:
    resource - information about a resource which should be included in the Slack notification. Example: {'service': 's3:bucket', 'id': 'bucket1', 'tags': [{'Key': 'Tag1Key', 'Value': 'Tag1Value' }], 'compliant_reasons': ["tag 'environment' does not exist", "tag 'project' does not exist"]}
    """
    tags_formated = []
    if resource['tags'] is not None:
        for t in resource['tags']: tags_formated.append(str(t['Key'] + " - " +t['Value']))

    payload = {
        "channel": SLACK_CHANNEL,
        "username": SLACK_USERNAME,
        "icon_url": SLACK_ICON_URL,
        "attachments": []
    }

    notification = {
        "color": "warning",
        "fallback": str("Resource " + resource['service'] + " " + resource['id'] + " is not compliant with tag policy"),
        "mrkdwn_in": ["text"],
        "fields": [
            { "title": "Service", "value": resource['service'], "short": True },
            { "title": "ID", "value": resource['id'], "short": False },
            { "title": "Reason", "value": "\n".join(resource['compliant_reasons']), "short": False },
            { "title": "Tags", "value": "\n".join(tags_formated), "short": False}
        ]
    }

    payload['text'] = "Tag Compliance"
    payload['attachments'].append(notification)

    data = urllib.parse.urlencode({"payload": json.dumps(payload)}).encode("utf-8")
    req = urllib.request.Request(SLACK_URL)

    if str2bool(ENABLE_Slack_Notifications):
        logging.info("Sending Slack message: " + str(payload))
        try:
            result = urllib.request.urlopen(req, data)
            return json.dumps({"code": result.getcode(), "info": result.info().as_string()})
        except HTTPError as e:
            logging.error("{}: result".format(e))
            return json.dumps({"code": e.getcode(), "info": e.info().as_string()})

def main():
    # EC2:Instance
    if str2bool(ENABLE_EC2_Instance):
        for r in get_ec2_instance_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # S3:Bucket
    if str2bool(ENABLE_S3_Bucket):
        for r in get_s3_bucket_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # DynamoDB:Table
    if str2bool(ENABLE_DynamoDB_Table):
        for r in get_dynamodb_table_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # ElastiCache:Node
    if str2bool(ENABLE_ElastiCache_Node):
        for r in get_elasticache_node_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # ElasticLoadBalancing:Loadbalancer
    if str2bool(ENABLE_ElasticLoadBalancing_Loadbalancer):
        for r in get_elb_loadbalancer_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # RDS:Cluster
    if str2bool(ENABLE_RDS_Cluster):
        for r in get_rds_cluster_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # SQS:Queue
    if str2bool(ENABLE_SQS_Queue):
        for r in get_sqs_queue_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

    # ElasticSearch:Cluster
    if str2bool(ENABLE_ElasticSearch_Cluster):
        for r in get_elasticsearch_cluster_resources():
            if not verify_tags_on_resource(r,REQUIRED_TAGS):
                notify_slack(r)

if __name__ == "__main__":
    main()