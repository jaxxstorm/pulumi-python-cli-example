import json
import pulumi
import pulumi_aws as aws


class WebAppArgs:
    """construct a webapp with arguments"""

    def __init__(
        self,
        image: str,
    ):
        self.image = image


class WebApp(pulumi.ComponentResource):
    def __init__(
        self, name: str, args: WebAppArgs, opts: pulumi.ResourceOptions = None
    ):

        super().__init__("webapp:index:Deployment", name, {}, opts)

        self.name = name
        self.vpc = aws.ec2.get_vpc(default=True)
        self.subnets = aws.ec2.get_subnet_ids(vpc_id=self.vpc.id)
        
        self.cluster = aws.ecs.Cluster(f"{name}-cluster", opts=pulumi.ResourceOptions(parent=self))

        self.security_group = aws.ec2.SecurityGroup(
            f"{name}-securitygroup",
            vpc_id=self.vpc.id,
            description="Enable HTTP access",
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=80,
                    to_port=80,
                    cidr_blocks=["0.0.0.0/0"],
                )
            ],
            egress=[
                aws.ec2.SecurityGroupEgressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                )
            ],
            opts=pulumi.ResourceOptions(parent=self)
        )

        self.alb = aws.lb.LoadBalancer(
            f"{name}-lb",
            security_groups=[self.security_group.id],
            subnets=self.subnets.ids,
            opts=pulumi.ResourceOptions(parent=self)
        )

        self.target_group = aws.lb.TargetGroup(
            f"{name}-tg",
            port=80,
            protocol="HTTP",
            target_type="ip",
            vpc_id=self.vpc.id,
            opts=pulumi.ResourceOptions(parent=self.alb)
        )

        self.listener = aws.lb.Listener(
            f"{name}-listener",
            load_balancer_arn=self.alb.arn,
            port=80,
            default_actions=[
                aws.lb.ListenerDefaultActionArgs(
                    type="forward",
                    target_group_arn=self.target_group.arn,
                )
            ],
            opts=pulumi.ResourceOptions(parent=self.alb)
        )

        self.role = aws.iam.Role(
            f"{name}-role",
            assume_role_policy=json.dumps(
                {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            opts=pulumi.ResourceOptions(parent=self)
        )

        self.attachment = aws.iam.RolePolicyAttachment(
            f"{name}-rpa",
            role=self.role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
            opts=pulumi.ResourceOptions(parent=self.role)
        )

        self.task_definition = aws.ecs.TaskDefinition(
            f"{name}-task-definition",
            family=name,
            cpu="256",
            memory="512",
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            execution_role_arn=self.role.arn,
            container_definitions=json.dumps(
                [
                    {
                        "name": name,
                        "image": args.image,
                        "portMappings": [
                            {"containerPort": 80, "hostPort": 80, "protocol": "tcp"}
                        ],
                    }
                ]
            ),
            opts=pulumi.ResourceOptions(parent=self.cluster)
        )

        self.service = aws.ecs.Service(
            f"{name}-svc",
            cluster=self.cluster.arn,
            desired_count=3,
            launch_type="FARGATE",
            task_definition=self.task_definition.arn,
            network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
                assign_public_ip=True,
                subnets=self.subnets.ids,
                security_groups=[self.security_group.id],
            ),
            load_balancers=[
                aws.ecs.ServiceLoadBalancerArgs(
                    target_group_arn=self.target_group.arn,
                    container_name=name,
                    container_port=80,
                )
            ],
            opts=pulumi.ResourceOptions(depends_on=[self.listener], parent=self.task_definition),
        )

        self.register_outputs({})
