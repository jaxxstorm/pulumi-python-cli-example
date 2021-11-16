"""An AWS Python Pulumi program"""
import argparse
import pulumi
import webapp
import sys

def pulumi_program():
    app = webapp.WebApp(name, webapp.WebAppArgs(image="nginx"))
    
    pulumi.export("url", app.alb.dns_name)

parser = argparse.ArgumentParser("Run a web application")
parser.add_argument("name",
                    metavar="name",
                    type=str,
                    help="the name of your running webapp")

parser.add_argument("--destroy", action="store_true", default=False)

args = parser.parse_args()

name = args.name

project_name = "webapp"
stack_name = name

stack = pulumi.automation.create_or_select_stack(stack_name=stack_name,
                                    project_name=project_name,
                                    program=pulumi_program)

print("successfully initialized stack")
print("installing plugins...")
stack.workspace.install_plugin("aws", "v4.27.2")
print("plugins installed")

print("setting up config")
stack.set_config("aws:region", pulumi.automation.ConfigValue(value="us-west-2"))
print("config set")

print("refreshing stack...")
stack.refresh(on_output=print)
print("refresh complete")


if args.destroy:
    print("destroying")
    stack.destroy(on_output=print)
    stack.workspace.remove_stack(name)
    print("stack destroy complete")
    sys.exit()

print("updating stack...")
up_res = stack.up(on_output=print)


