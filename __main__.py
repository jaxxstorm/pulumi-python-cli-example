"""An AWS Python Pulumi program"""

import pulumi
import webapp

webapp = webapp.WebApp("example", webapp.WebAppArgs(image="nginx"))

pulumi.export("url", webapp.alb.dns_name)


