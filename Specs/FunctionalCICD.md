The program and infrastructure should include the following steps::
1. Preparation of a local runner:
Installing Docker and deploying a local executor. GitLab CI
uses the official gitlab/gitlab-runner image linked to a Docker
socket. The act utility is used for GitHub Actions.
2. Build Stage:
Compiling the source code of the test application (Python) **inside the container**.
3. Testing stage (Test):
Running unit tests with report generation in JUnit or Cobertura format.
4. Security Stage (SAST):
Launching a vulnerability scanner. When problems of the High or Critical level
are found, **the job should end with an error**.
5. The deployment stage (Local Deployment):
Building a Docker image of the application and running it locally with port forwarding
