Project structure requirements
1. Dockerfile:
Multi-stage build to minimize the size
of the final image.
Running the application as an unprivileged user inside
the container.
2. CI/CD configuration file ( .gitlab-ci.yml or .github/workflows/main.yml ):
Explicit declaration of stages.
Using artifacts to transfer data between stages.
Using the cache for directories with dependencies.
3. Test Application:
Developed file manager code
