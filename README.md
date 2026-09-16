# Idempotent_Purchases
A backend service that sells limited-stock items under heavy concurrent load, while guaranteeing that a single logical purchase attempt — even if retried multiple times due to network failure — is applied exactly once.
