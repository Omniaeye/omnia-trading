# Security

Keep source archives and decision ledgers in private storage. Input text is not
written into the shared decision ledger; source identifiers and answer labels are.
Treat those identifiers as application data, not anonymized records.

Do not put credentials, private URLs, wallet keys or account data in evidence.
The CLI never follows source URLs, opens a public listener or executes instructions
from source content. It emits error types rather than raw provider exceptions.
Reviewed checkpoints and trusted package code are execution dependencies.

Report vulnerabilities privately through GitHub's **Report a vulnerability**
feature when enabled. Do not include secrets in public issues.
