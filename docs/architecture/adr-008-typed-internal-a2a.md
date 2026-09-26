# ADR 008: Typed internal agent messages; formal A2A protocol deferred

Status: Proposed  
Date: 2026-09-26

## Context

The brief asks for agent-to-agent (A2A) communication. It is unconfirmed whether the assessor expects the standardized Agent2Agent protocol.

## Options

- **Implement the formal A2A protocol now.** Interoperability claim; discovery/transport work before the core works.
- **Typed internal messages with recorded handoffs.** Demonstrates real exchanges; no interoperability claim.

## Decision

Agents exchange `AgentExchange` messages (sender, recipient, type, causal parent, payload, remaining repair rounds), persisted in `agent_messages` and shown in the trace. Documentation must say these are application-level messages, not the standardized protocol.

## Consequences

No claim of protocol interoperability can be made.

## Revisit when

The assessor confirms the rubric requires the standard protocol: implement F28.
