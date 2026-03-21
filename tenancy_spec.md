Multi-Tenant Organization and Workspace Access Control Specification
1. Purpose

This specification defines the tenancy, identity, membership, role, and authorization rules for a multi-tenant platform with the following hierarchy:

Platform
Organization
Workspace

The system supports:

a global Platform Admin
multiple Organizations
multiple Workspaces under each Organization
users belonging to multiple Organizations
users belonging to multiple Workspaces
role-based access control at platform, organization, and workspace levels

This document defines the rules, boundaries, role model, and governance expectations. It does not define implementation details or code.

2. Design Goals

The access model must support:

Strong tenant isolation between Organizations
Flexible collaboration across Organizations and Workspaces
Scoped administration at platform, organization, and workspace levels
Least privilege by default
Clear inheritance rules
Auditable access changes
Extensibility for future custom roles or policy overlays


3. Core Concepts
3.1 Platform

The Platform is the top-level system boundary that contains all Organizations, Workspaces, Users, roles, and global settings.

The Platform has one or more Platform Admins.

Platform Admins have cross-tenant visibility and control, subject to audit.

3.2 Organization

An Organization is the primary tenant boundary.

An Organization:

owns its Workspaces
has its own users, memberships, roles, and settings
is isolated from other Organizations
may contain many Workspaces
may contain many users
may share users with other Organizations through separate memberships

Each Organization must have at least one Org Admin.

A default Organization exists and is controlled by the Platform Admin at system bootstrap.

3.3 Workspace

A Workspace is a sub-scope within an Organization.

A Workspace:

belongs to exactly one Organization
cannot span multiple Organizations
has its own membership list and roles
is used for team, project, environment, product, or business-unit level segmentation

Each Workspace belongs to one and only one Organization.

A Workspace may have multiple Workspace Admins.

3.4 User

A User is a human identity recognized by the platform.

A User:

may belong to zero, one, or many Organizations
may belong to zero, one, or many Workspaces
may have different roles in different Organizations
may have different roles in different Workspaces
may hold multiple roles where allowed by policy

A User identity is global to the Platform, but authorization is always evaluated in scope.

3.5 Membership

Membership is the association between a User and a scope.

Membership scopes:

Platform membership
Organization membership
Workspace membership

A User must be explicitly associated with a scope to operate in that scope, unless access is granted through a higher-level administrative role.

3.6 Role

A Role is a named collection of permissions assigned within a specific scope.

Role scopes:

Platform-scoped roles
Organization-scoped roles
Workspace-scoped roles

A role assignment must always specify:

user
role
scope
assignment source
status
created by
created at
4. Tenancy Model
4.1 Hierarchy

The logical hierarchy is:

Platform -> Organization -> Workspace

Rules:

Every Workspace must belong to exactly one Organization.
Every Organization may contain zero or more Workspaces.
A User may belong to multiple Organizations.
A User may belong to multiple Workspaces.
A User may belong to a Workspace only if they are also a member of the parent Organization.
Removing a User from an Organization must also remove or invalidate all their memberships in that Organization’s Workspaces.


4.2 Tenant Isolation Rules

Organizations are the primary isolation boundary.

Rules:

Users in one Organization must not see resources of another Organization unless they also hold membership in that other Organization.
Workspace data must never be shared across Organizations.
Workspace identifiers may be globally unique or Org-unique, but authorization must always validate the parent Organization.
Org-scoped settings must not affect other Organizations.
Platform Admins may traverse tenant boundaries for administrative purposes, but all such actions must be audited.
5. Administrative Model
5.1 Platform Admin

Platform Admin is the highest authority in the system.

Platform Admin capabilities include:

create, update, suspend, and delete Organizations
create the initial Org Admin for an Organization
manage global platform settings
manage global role definitions if the platform supports centrally managed roles
view platform-wide audit records
impersonate or troubleshoot access, subject to audit policy
manage the default Organization
assign or revoke Platform Admin privileges
act as Org Admin for the default Organization

Rules:

Platform Admin authority applies across all Organizations.
Platform Admin actions must be logged with high audit priority.
Platform Admin should be a restricted role assigned to a minimal number of trusted operators.
Platform Admin should not be used for routine Organization operations where Org Admin is sufficient.


5.2 Default Organization

A default Organization exists at system initialization.

Rules:

The Platform Admin is also an Org Admin of the default Organization.
The default Organization behaves like any other Organization unless explicitly designated for special internal platform use.
The default Organization may be used for:
platform internal operations
bootstrap setup
internal teams
default landing context for users without another Org
If used as a normal Organization, the same RBAC and audit rules apply.


5.3 Org Admin

Org Admin is the highest administrative role within an Organization.

Org Admin capabilities include:

manage Organization settings
invite, add, remove, suspend users within the Organization
assign Organization-level roles
create, update, archive, and delete Workspaces in the Organization
assign Workspace Admins
view Organization audit trails
define Organization-specific policies if supported
manage billing or subscription data if billing is org-scoped

Rules:

Each Organization must have at least one active Org Admin.
Platform Admin creates the initial Org Admin for a new Organization.
Org Admin authority is limited to the Organization in which it is assigned.
Org Admin cannot alter global platform settings unless also a Platform Admin.
Org Admin may grant Workspace roles only within Workspaces of their Organization.


5.4 Workspace Admin

Workspace Admin is the highest administrative role within a Workspace.

Workspace Admin capabilities include:

manage Workspace settings
add or remove Workspace members, subject to Org membership rules
assign Workspace-level roles
manage Workspace resources and governance
view Workspace activity and audit records

Rules:

Workspace Admin authority is limited to their assigned Workspace.
Workspace Admin cannot administer sibling Workspaces unless explicitly assigned there.
Workspace Admin cannot grant Organization-level roles.
Workspace Admin may add only users who are already members of the parent Organization, or initiate a request flow that requires Org Admin approval.

6. Recommended Role Model

A simple and scalable model is to define roles at each scope.

6.1 Platform Roles
6.1.1 Platform Admin

Full system administration across all tenants and scopes.

6.1.2 Platform Operator

Operational support role with limited global privileges, such as monitoring, support, diagnostics, or audit viewing, but without full tenant governance authority.

This role is optional but strongly recommended if you want separation between platform operations and full super-admin power.

6.1.3 Platform Auditor

Read-only access to platform-wide audit logs, compliance views, and governance reports.

Optional role.

6.2 Organization Roles
6.2.1 Org Admin

Full administration of one Organization and its Workspaces.

6.2.2 Org Manager

Operational manager within an Organization.

Typical capabilities:

view Org membership
manage some Org metadata
create Workspaces
manage selected users
read reports

Cannot perform the most sensitive actions unless separately allowed.

6.2.3 Org Member

Standard Organization user.

Typical capabilities:

view the Organization they belong to
access Org-shared features allowed to members
request Workspace access
participate in org-level non-admin flows


6.2.4 Org Billing Admin

Manages subscriptions, invoices, payment methods, quotas, and commercial settings for an Organization.

Optional role.

6.2.5 Org Auditor

Read-only access to Organization-level compliance, audit, and governance information.

Optional role.

6.3 Workspace Roles
6.3.1 Workspace Admin

Full administration of one Workspace.

6.3.2 Workspace Editor

Can create, modify, and manage business objects or content inside the Workspace, but cannot manage Workspace membership or sensitive settings unless explicitly allowed.

6.3.3 Workspace Contributor
Can contribute to workspace resources with narrower privileges than Editor.

6.3.4 Workspace Viewer

Read-only access to Workspace resources.

6.3.5 Workspace Analyst

Read and analyze data, reports, dashboards, and metrics, but may not modify core resources.

Optional role depending on product needs.

7. Role Scope Principles
7.1 Scope Boundaries

Roles are valid only within the scope in which they are assigned.

Examples:

a User may be Org Admin in Org A and only Org Member in Org B
a User may be Workspace Admin in Workspace X and Workspace Viewer in Workspace Y
a User may be Org Member in an Organization without belonging to any Workspace
7.2 Scope Precedence

Authorization should evaluate the narrowest relevant scope first, then broaden if needed.

Recommended precedence:

Explicit deny, if deny rules exist
Platform role
Organization role
Workspace role
Resource-specific override, if supported

For simplicity, most systems should avoid complex explicit deny semantics unless necessary.


7.3 Role Inheritance

Recommended inheritance rules:

Platform Admin implicitly has admin rights across all Organizations and Workspaces.
Org Admin implicitly has administrative authority over all Workspaces in that Organization, even if not explicitly added to each Workspace.
Non-admin Organization roles do not automatically grant Workspace access.
Workspace roles do not grant Organization administrative privileges.
Workspace membership requires Organization membership.

This keeps the model intuitive.

8. Membership Rules
8.1 Organization Membership

A User may be added to an Organization by:

Platform Admin
Org Admin
automated provisioning flow
invitation flow
approved federation or directory sync flow

Rules:

Org membership must exist before Workspace membership.
Users may be active in multiple Organizations simultaneously.
Org membership status should support:
invited
active
suspended
removed
Suspended Org membership must suspend effective access to all child Workspaces.

8.2 Workspace Membership

A User may be added to a Workspace only if they are already an active member of the parent Organization.

Rules:

A User may be a member of multiple Workspaces under the same Organization.
A User may be a member of Workspaces across different Organizations, provided they hold Org membership in each parent Organization.
Workspace membership status should support:
invited
active
suspended
removed
Removing a User from a Workspace does not remove them from the parent Organization.
Removing a User from the Organization must remove all downstream Workspace memberships in that Organization.


8.3 Multi-Organization User Rules

The same User identity may exist in many Organizations.

Rules:

Membership and roles must be independent per Organization.
A User’s role in one Organization must not influence authorization in another Organization.
UI and APIs should require a clear current Organization context to prevent accidental cross-tenant actions.
Audit logs must record the active Organization and Workspace context for every action.

9. Recommended Authorization Rules
9.1 High-Level Rule

A User may perform an action only if all of the following are true:

the User identity is active
the User has valid membership in the relevant scope, unless elevated by a higher-scope admin role
the assigned role grants the required permission
the target resource belongs to the evaluated scope
no suspension, lock, or policy restriction blocks the action

9.2 Organization Access Rules

A User can access an Organization if:

they are a Platform Admin, or
they hold active membership in that Organization

A User can administer an Organization if:

they are a Platform Admin, or
they are an Org Admin for that Organization

9.3 Workspace Access Rules

A User can access a Workspace if:

they are a Platform Admin, or
they are an Org Admin of the parent Organization, or
they hold active membership in the parent Organization and active membership in the Workspace

A User can administer a Workspace if:

they are a Platform Admin, or
they are an Org Admin of the parent Organization, or
they are a Workspace Admin in that Workspace

10. Permission Categories

Instead of binding the system forever to current role names, permissions should be grouped into categories.

Recommended permission groups:

10.1 Platform Permissions
manage platform settings
manage Organizations
manage platform users
manage platform roles
view platform audit logs
perform tenant support actions
impersonate users, if allowed
10.2 Organization Permissions
view Organization
edit Organization settings
manage Org membership
manage Org roles
create Workspaces
archive Workspaces
view Org reports
manage billing
view Org audit logs

10.3 Workspace Permissions
view Workspace
edit Workspace settings
manage Workspace membership
manage Workspace roles
create workspace resources
modify workspace resources
delete workspace resources
view workspace analytics
export workspace data
view workspace audit logs

11. Role-to-Permission Guidance
11.1 Platform Admin

Should have all platform, organization, and workspace permissions.

11.2 Platform Operator

Should have operational but not governance-critical permissions unless explicitly allowed.

11.3 Org Admin

Should have all organization permissions and inherited workspace administration for all Workspaces in the Organization.

11.4 Org Manager

Should have selected Organization permissions but not the ability to remove the last Org Admin, transfer ownership, or change the most sensitive org settings.

11.5 Org Member

Should have basic Organization visibility and participation only.

11.6 Workspace Admin

Should have all permissions within that Workspace, but no Organization-wide control.

11.7 Workspace Editor

Should manage content, not governance.

11.8 Workspace Contributor

Should contribute but with more restricted modify/delete capabilities.

11.9 Workspace Viewer

Should have read-only access.


12. Critical Governance Rules
12.1 Last Admin Protection

The system must prevent accidental loss of tenant administration.

Rules:

An Organization must never be left without at least one active Org Admin.
A Workspace should preferably have at least one Workspace Admin, unless Org Admin inheritance is considered sufficient.
The system must block role removal, suspension, or user removal if it would leave the Organization without an active Org Admin.
Platform Admin may override this only through an audited break-glass flow.

12.2 Separation of Duties

Recommended for enterprise-grade governance.

Rules:

Billing privileges should be separable from general Org Admin privileges.
Audit-read privileges should be separable from modification privileges.
Platform operations should be separable from Platform Admin where possible.
12.3 Auditability

All membership and role changes must be auditable.

Audit events should include:

actor
target user
target scope
old role or membership
new role or membership
timestamp
reason if required
source system or workflow

High-sensitivity actions that must always be logged:

create or delete Organization
create or delete Workspace
assign or revoke Platform Admin
assign or revoke Org Admin
assign or revoke Workspace Admin
suspend or remove user access
impersonation or support override actions
12.4 Least Privilege

Rules:

Users should receive the lowest role needed to perform their function.
Default invitation role should be non-admin.
Admin roles should require explicit assignment.
No user should automatically become admin merely by joining an Organization or Workspace.
13. Invitation and Provisioning Rules
13.1 Organization Invitation

A User may be invited to an Organization by Platform Admin or Org Admin.

Rules:

Invitation must specify Organization and initial Org role.
If no role is specified, default to Org Member.
Invitation acceptance activates Organization membership.
If the invited email matches an existing User, attach membership to that existing identity.
If no identity exists, create one through signup or claim flow.
13.2 Workspace Invitation

A User may be invited to a Workspace by Org Admin or Workspace Admin.

Rules:

Workspace invitation requires active Organization membership.
If the user is not yet an Org member, the system should either:
reject the invite, or
convert it into a combined Org + Workspace invite flow
Default workspace role should be Viewer or Contributor, not Admin.
14. Lifecycle Rules
14.1 Organization Lifecycle

Supported states may include:

active
suspended
archived
deleted

Rules:

Suspended Organizations block member access.
Archived Organizations are read-only unless restored.
Deleting an Organization is a high-risk action and should require Platform Admin authority.
Deletion policy should define whether data is soft-deleted, retained, or permanently purged.
14.2 Workspace Lifecycle

Supported states may include:

active
suspended
archived
deleted

Rules:

Archived Workspaces should be read-only.
Deleted Workspaces should no longer be accessible.
Workspace lifecycle cannot outlive the parent Organization lifecycle in contradiction.
If an Organization is suspended, its Workspaces are effectively suspended too.
14.3 User Lifecycle

Supported user access states may include:

invited
active
suspended
deactivated
removed

Rules:

A suspended user loses effective access in all scopes where suspension applies.
Deactivating a global user account disables all org/workspace access.
Removing Org membership removes all child Workspace memberships in that Organization.
15. Recommended Effective Role Resolution

When a user accesses a Workspace resource, effective access should be computed using:

user identity status
organization status
workspace status
platform-level roles
organization-level roles
workspace-level roles
applicable policy restrictions

Recommended logic:

Platform Admin: full access
Org Admin of parent Org: full workspace admin access
Explicit Workspace role: access per that role
Org Member without Workspace membership: no workspace access unless the workspace is marked open to all org members
No parent Org membership: no access
16. Optional Model Extension: Open vs Restricted Workspaces

You may optionally support two workspace access modes:

16.1 Restricted Workspace

Only explicitly assigned workspace members may access it.

16.2 Open Workspace

Any member of the parent Organization may access it with a baseline role such as Viewer.

Rules:

Workspace access mode must be explicit.
Admin rights still require explicit admin role or Org Admin inheritance.
Sensitive Workspaces should default to Restricted.

This is optional but useful.

17. Constraints and Invariants

The following must always remain true:

Every Workspace belongs to exactly one Organization.
A Workspace member must also be a member of the parent Organization.
A User may belong to multiple Organizations.
A User may belong to multiple Workspaces.
Organization isolation must be preserved.
An Organization must have at least one active Org Admin.
Platform Admin may act across Organizations.
Role assignments are scope-bound.
Removing Organization membership removes child Workspace memberships.
Authorization must always validate scope ownership of the target resource.
18. Recommended Minimum Role Set

If you want a clean first version, use this minimum set:

Platform
Platform Admin
Organization
Org Admin
Org Member
Workspace
Workspace Admin
Workspace Editor
Workspace Viewer

This is enough for most MVPs.

If you want a slightly richer but still manageable model:

Platform
Platform Admin
Platform Operator
Organization
Org Admin
Org Manager
Org Member
Org Billing Admin
Org Auditor
Workspace
Workspace Admin
Workspace Editor
Workspace Contributor
Workspace Viewer
19. Recommended Product Decisions

For clarity and scalability, the following product decisions are recommended:

Use Organization as the hard tenant boundary
Use Workspace as a collaboration/project boundary
Make Org membership mandatory before Workspace membership
Allow Org Admin to inherit Workspace admin authority
Keep default roles simple
Prevent automatic privilege escalation
Require full audit logging for all access changes
Support multi-org membership per user
Require explicit current Org context in UI and API
Protect against last-admin removal
20. Example Scenarios
20.1 Platform Admin Creates a New Organization
Platform Admin creates Org A
Platform Admin assigns Alice as initial Org Admin
Alice can now manage Org A and create Workspaces
Alice has no rights in Org B unless separately assigned
20.2 User Belongs to Multiple Organizations
Bob is Org Member in Org A
Bob is Org Admin in Org B
Bob’s permissions differ by active Organization context
Bob cannot administer Org A based on his Org B role
20.3 User Belongs to Multiple Workspaces
Carol is Org Member in Org A
Carol is Workspace Editor in Workspace X
Carol is Workspace Viewer in Workspace Y
Carol’s permissions differ by workspace
20.4 Org Admin Implicitly Administers Workspaces
David is Org Admin in Org A
Workspace X and Y exist under Org A
David can administer both even if not explicitly added to each Workspace
20.5 Removing Organization Membership
Eve belongs to Org A and Workspaces X and Y
Eve is removed from Org A
Eve automatically loses access to X and Y
21. Non-Goals

This specification does not define:

authentication protocol details
SSO/SAML/OIDC mapping rules
database schema
API contract design
UI design
implementation code
custom policy DSL

These may be defined in separate specifications.

22. Final Recommended Rule Summary

The system shall operate under these core rules:

The Platform contains multiple Organizations.
Each Organization contains multiple Workspaces.
Each Workspace belongs to exactly one Organization.
Platform Admin is the global super-admin role.
Platform Admin creates Organizations and the initial Org Admin.
Platform Admin is Org Admin for the default Organization.
A User may belong to multiple Organizations.
A User may belong to multiple Workspaces.
A User must belong to an Organization before joining its Workspace.
Org Admin governs the Organization and all its Workspaces.
Workspace Admin governs only the assigned Workspace.
Roles are scoped and do not automatically apply outside their scope.
Organization isolation is mandatory.
Removing Org membership removes all child Workspace memberships.
At least one active Org Admin must always exist per Organization.
All role and membership changes must be auditable.