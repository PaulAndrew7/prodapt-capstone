# ADR 005: Local reactive avatar

Status: Accepted  
Date: 2026-09-26

## Context

The avatar is a showcase feature. It must react to real workflow events without adding a paid dependency or blocking the core task.

## Options

- **Cloud video avatar.** Photoreal; cost, latency, privacy and availability risk.
- **Local Three.js figure driven by a pure event controller.** Less realistic; free, fast, testable, degrades cleanly.

## Decision

The web app renders a procedural figure with React Three Fiber, lazy-loaded, driven by `features/avatar/controller.ts` from the same run events as the workspace. All tasks work with the avatar off or failing.

## Consequences

Less visual fidelity than video avatars.

## Revisit when

User testing shows a video avatar adds value and a budget exists for it.
