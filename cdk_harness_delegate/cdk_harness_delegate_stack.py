import os
import json
import logging as log
from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam

def getHarnessTask():
    try:
        with open('ecs-task-spec.json', 'r') as ecsfile:
            harness_delegate_download = json.load(ecsfile)
    except Exception as no_task_error:
        log.error("{} harness delegate task file not found: https://docs.harness.io/article/wrm6hpyrjl-harness-ecs-delegate#set_up_ecs_delegate_in_aws".format(no_task_error))

    return harness_delegate_download

def getHarnessEnv():
    harnness_env_vars = {}
    for container_defs in getHarnessTask()['containerDefinitions']:
        for henv in container_defs['environment']:
            harnness_env_vars[henv['name']] = henv['value']
    return harnness_env_vars
class CdkHarnessDelegateStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the VPC 
        vpc = ec2.Vpc(
            self, "harnessVPC",
            max_azs = 2,
            subnet_configuration = [ec2.SubnetConfiguration(
                name = 'harnessPrivateSubnet',
                subnet_type = ec2.SubnetType.PRIVATE
            ),
            ec2.SubnetConfiguration(
                name = 'harnessPublicSubnet',
                subnet_type = ec2.SubnetType.PUBLIC
            )]
        )

        ecs_exec_role = iam.Role(self, "harnessECSExecutionRole", assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"))
        # cluster_role = iam.Role.from_role_arn(
        #     self, 
        #     'Role', 
        #     'arn:aws:iam::626449308506:role/ecsInstanceRole'
        # )

        ecs_exec_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonEC2ContainerServiceRole'))
        ecs_exec_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonECSTaskExecutionRolePolicy'))
        ecs_exec_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonEC2ContainerServiceforEC2Role'))
        ecs_exec_role.add_to_policy(iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            actions = [
                "ecr:DescribeRepositories",
                "ecs:ListClusters",
                "ecs:ListServices",
                "ecs:DescribeServices",
                "ecr:ListImages",
                "ecs:RegisterTaskDefinition",
                "ecs:CreateService",
                "ecs:ListTasks",
                "ecs:DescribeTasks",
                "ecs:CreateService",
                "ecs:DeleteService",
                "ecs:UpdateService",
                "ecs:DescribeContainerInstances",
                "ecs:DescribeTaskDefinition",
                "application-autoscaling:DescribeScalableTargets",
                "iam:ListRoles",
                "iam:PassRole"
                ],
            resources = ["*"],
        ))


        ## Create the ECS Cluster
        cluster = ecs.Cluster(
            self, "harnessCluster",
            vpc = vpc
        )

        # ## Create a ECS Task role
        # ecs_task_role = iam.Role(self, "harnessECSTaskRole", assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"))

        # ecs_task_role.add_to_policy(iam.PolicyStatement(
        # effect = iam.Effect.ALLOW,
        # actions = [
        #     "ecr:GetAuthorizationToken",
        #     "ecr:BatchCheckLayerAvailability",
        #     "ecr:GetDownloadUrlForLayer",
        #     "ecr:BatchGetImage",
        #     "logs:CreateLogStream",
        #     "logs:PutLogEvents"
        #     ],
        # resources = ["*"],
        # ))

        task_definition = ecs.TaskDefinition(
            self, 
            'harnessFargateTask',
            compatibility = ecs.Compatibility('FARGATE'),
            execution_role = ecs_exec_role,
            task_role = ecs_exec_role,
            memory_mib = '6144', 
            cpu = '1024'
        )

        task_definition.add_container(
            'harnessContainer',
            image = ecs.ContainerImage.from_registry('harness/delegate:latest'),
            environment = getHarnessEnv()
        )

        app = ecs.FargateService(
            self,
            'harnessDelegate',
            cluster = cluster,
            assign_public_ip = False,
            desired_count = 1,
            task_definition = task_definition
        )