modules = ["python-3.11", "python3"]

[nix]
channel = "stable-24_05"

[deployment]
deploymentTarget = "autoscale"
run = ["gunicorn", "--bind", "0.0.0.0:5000", "server:application"]

[workflows]
runButton = "Start application"

[[workflows.workflow]]
name = "Start application"
author = "agent"

[workflows.workflow.metadata]
agentRequireRestartOnSave = false

[[workflows.workflow.tasks]]
task = "packager.installForAll"

[[workflows.workflow.tasks]]
task = "shell.exec"
args = "python server.py"
waitForPort = 5000

[[ports]]
localPort = 5000
externalPort = 80

[[ports]]
localPort = 8000
externalPort = 8000