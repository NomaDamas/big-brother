# Operator Guide

This guide will grow with the implementation. The first release target is a
single Linux server with an NVIDIA GPU and Docker Compose.

## Prerequisites

- Supported Ubuntu LTS release.
- NVIDIA driver installed by the operator.
- NVIDIA Container Toolkit installed by the operator.
- Docker and Docker Compose.

## Operating principles

- Keep the service local unless a later deployment explicitly enables remote
  integrations.
- Import only authorized hash lists.
- Use synthetic fixtures for tests and demos.
- Route uncertain model output to review.
- Review audit logs after every policy change.

