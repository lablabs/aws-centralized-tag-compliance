import main
import pytest
from os import environ
from json import loads

@pytest.fixture(scope='module', autouse=True)
def check_environment_variables():
    required_environment_variables = ("SLACK_CHANNEL", "SLACK_EMOJI", "SLACK_USERNAME", "SLACK_WEBHOOK_URL")
    missing_environment_variables = []
    for k in required_environment_variables:
        if k not in environ:
            missing_environment_variables.append(k)

    if len(missing_environment_variables) > 0:
        pytest.exit('Missing environment variables: {}'.format(", ".join(missing_environment_variables)))

@pytest.mark.parametrize(
    "required_tag_key,tags_input,expected",
    [
        ("environment",[{"Key": "environment", "Value": "prod"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], True),
        ("environment",[{"Key": "environment", "Value": "*"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], True),
        ("environment",[{"Key": "service", "Value": "k8s"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], False),
        ("environment", None, False)
    ]
)
def test_check_if_tag_exists(required_tag_key,tags_input,expected):
    assert main.check_if_tag_exists(tags_input,required_tag_key) == expected

@pytest.mark.parametrize(
    "required_tag_key,required_tag_values,tags_input,expected",
    [
        ("environment",["prod", "dev", "test"],[{"Key": "environment", "Value": "prod"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], True),
        ("environment",["*", "dev"],[{"Key": "environment", "Value": "dev"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], True),
        ("environment",["*"],[{"Key": "environment", "Value": "unknown"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], True),
        ("environment",["prod", "dev", "test"],[{"Key": "environment", "Value": "unknown"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], False),
        ("environment",["prod", "dev", "test"],[{"Key": "project", "Value": "unknown"}, {"Key": "KubernetesCluster", "Value": "kube.prod.pxfd.tech"}, {"Key": "project", "Value": "da"}], False),
        ("environment",["prod", "dev", "test"], None, False)
    ]
)
def test_check_if_tag_is_compliant(required_tag_key,required_tag_values,tags_input,expected):
    assert main.check_if_tag_is_compliant(tags_input,required_tag_key,required_tag_values) == expected

@pytest.mark.parametrize(
    "resource,required_tags,expected",
    [
        (
            {"service": "ec2:instance", "id": "i-1111", "tags": [{"Key": "Name", "Value": "da-nodes.kube.prod.pxfd.tech"}, {"Key": "environment", "Value": "prod"}, {"Key": "Project", "Value": "p1"}]},
            [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":["prod", "dev"]}],
            True
        ),
        (
            {"service": "ec2:instance", "id": "i-1111", "tags": [{"Key": "Name", "Value": "da-nodes.kube.prod.pxfd.tech"}, {"Key": "environment", "Value": "prod"}, {"Key": "Project", "Value": "p1"}]},
            [{"key": "Project","values":["*"]},{"key": "environment","values":["prod", "dev"]}],
            True
        ),
        (
            {"service": "ec2:instance", "id": "i-2222", "tags": [{"Key": "Name", "Value": "da-nodes.kube.prod.pxfd.tech"}, {"Key": "environment", "Value": "prod"}, {"Key": "project", "Value": "unknown"}]},
            [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":[ "prod", "dev"]}],
            False
        ),
        (
            {"service": "ec2:instance", "id": "i-3333", "tags": [{"Key": "Name", "Value": "da-nodes.kube.prod.pxfd.tech"}, {"Key": "environment", "Value": "unknown"}, {"Key": "project", "Value": "unknown"}]},
            [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":[ "prod", "dev"]}],
            False
        ),
        (
            {"service": "ec2:instance", "id": "i-4444", "tags": [{"Key": "Name", "Value": "da-nodes.kube.prod.pxfd.tech"}, {"Key": "environment", "Value": "prod"}]},
            [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":[ "prod", "dev"]}],
            False
        ),
        (
            {"service": "ec2:instance", "id": "i-5555", "tags": None},
            [{"key": "Project","values":["p1", "p2"]},{"key": "environment","values":[ "prod", "dev"]}],
            False
        ),
    ]
)
def test_verify_tags(resource,required_tags,expected):
    assert main.verify_tags_on_resource(resource,required_tags) == expected

@pytest.mark.parametrize(
    "resource",
    [
        #({'service': 's3:bucket', 'id': 'bucket1', 'tags': [{'Key': 'owner', 'Value': 'mvince'}, {'Key': 'env', 'Value': 'sandbox'}], 'compliant_reasons': ["tag 'environment' does not exist", "tag 'project' does not exist"]}),
        ({'service': 's3:bucket', 'id': 'bucket2', 'tags': [{'Key': 'kubernetes.io/service-name', 'Value': 'gitlab/gitlab-gitlab-shell' }], 'compliant_reasons': ["tag 'environment' does not exist", "tag 'project' does not exist"]}),
    ]
)
def test_slack_notify(resource):
    response = loads(main.notify_slack(resource))
    assert response['code'] == 200