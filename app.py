#!/usr/bin/env python3

from aws_cdk import core

from cdk_harness_delegate.cdk_harness_delegate_stack import CdkHarnessDelegateStack


app = core.App()
CdkHarnessDelegateStack(app, "cdk-harness-delegate")

app.synth()
