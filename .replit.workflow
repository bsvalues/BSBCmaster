modules = ["python-3.11", "python3"]

[nix]
channel = "stable-24_05"

[deployment]
deploymentTarget = "autoscale"
run = ["python", "workflow.py"]

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
args = "python workflow.py"
waitForPort = 5000

[[ports]]
localPort = 5000
externalPort = 80

[[ports]]
localPort = 8000
externalPort = 8000