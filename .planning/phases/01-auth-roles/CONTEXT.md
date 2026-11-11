# Phase 1: Authentication, Authorization and Roles - Context

## Objective
Implement secure user persistence, Argon2 password hashing, short-lived JWT issuance, server-side role resolution on every request, `require_role` FastAPI dependency, seeded accounts across all four roles, and permission verification service.

## Security Constraints (Blueprint Sections 4.4 & 6.4)
- Passwords hashed using Argon2 with minimum length of 10 characters.
- Short-lived JWT (30 minutes) carrying user_id only.
- Roles are NEVER trusted from JWT payload alone; active user status and role are read directly from the database on every authenticated request.
- `require_role` dependency on protected routes; non-admin accessing forbidden document routes receives 404 (or 403 where appropriate) so restricted assets are not disclosed.

