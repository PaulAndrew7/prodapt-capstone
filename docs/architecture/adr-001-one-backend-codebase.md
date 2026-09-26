# ADR 001: One backend codebase with API and worker processes

Status: Accepted  
Date: 2026-09-26

## Context

The brief asks for five specialist agents and describes the deliverable as a "microservice". Agents need shared contracts, one database, durable jobs and a single evidence model. The team is one student directing coding agents, on a five-day deadline.

## Options

- **One service per agent.** Independent deploys, but five sets of contracts, networking, auth and failure modes to integrate and test.
- **One FastAPI service plus a worker process from the same package.** Agents stay separate modules with typed contracts; one release, one migration history.

## Decision

Build `services/api` as one Python package. The HTTP API (`uvicorn app.main:app`) and the workflow/ingestion worker are separate processes started from the same image. Agents are modules under `app/agents` with their own input/output contracts and recorded handoffs (see ADR 008).

## Consequences

Agents share a release cycle and a dependency set. A slow agent cannot be scaled independently. The "microservice" requirement is met by an independently runnable, containerized API with its own database, which the README must explain.

## Revisit when

Separate teams own agents, or a measured bottleneck needs one agent scaled on its own.
