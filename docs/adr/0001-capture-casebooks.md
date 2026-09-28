# Capture casebooks and installed reporting

Status: accepted. Date: 28 September 2026.

## Decision

Keep the decision engine API stable. Move the report builder into the installed
package and expose capture publication through a separate casebook interface.
Retain the existing script command as a compatibility launcher.

A casebook stores the complete selected cohort, exact native requests and
responses, every report series, source hashes and calculated exit events.
Model answers, market price changes and position-policy calculations remain
separate records. Source timestamps and original responses are not rewritten
when a later engine version changes its requirements.

## Reasons

Importing an executable tool by file path made report tests depend on checkout
layout. Public users could read policies but could not inspect the recorded
window. The installed module now owns report generation and its template;
the casebook module owns export, provenance checks and deterministic replay.

Tests follow these interfaces, grouped by responsibility. No test is removed
solely to reduce the number of files. Shared runtime fingerprints remain intact.

## Consequences

The source distribution includes the public casebook so offline verification
works from a checkout or source archive. Wheels contain the engine and report
template; large example datasets remain separate from the runtime installation.
The full provider archive is not included in either distribution.
