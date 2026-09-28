# Public source namespaces

OMNIA exposes stable source names independently of its collection transports.

| Namespace | Contract |
| --- | --- |
| `omnia.market.rank` | Normalized market-ranking observations |
| `omnia.market.security` | Token-scoped security observations |
| `omnia.news` | Attributed publication assessments |

The casebook exporter validates original captures before applying the public
namespace. Every projected observation includes `archived_event_sha256`, the
fingerprint of the source event before projection, and the projection version.
The public event and casebook files receive their own integrity hashes.

Changing a display namespace does not change the capture's origin, evidence,
clock, native model response or market trajectory. Original transport provenance
remains in the private collection archive. Historical Git objects remain intact.

Source field conversions are explicit. A declared 0/1 security flag may become a
boolean only under the recorded reviewed source contract. An arbitrary number or
similarly named field is not accepted as a security verdict.
