# Setup and discoverability

Product defaults must work for a new person, account and Fabric. Developer
usernames, hostnames, addresses, drive IDs, credentials and private preferences
belong in that user's local configuration, never operational templates or defaults.
Historical diagnostics may describe a particular installation; user-facing guides
and generated jobs must derive choices from the current user's environment.

Expose setup where people look for it: Settings, command help, and the relevant
feature's empty state. Explain the purpose and scope before presenting choices.
Discover resources when the person opens the setup flow; plugging in hardware
must not silently launch, authorize, initialize or format anything.

Prefer a short guided path over instructions to edit JSON, remember UUIDs or
substitute private identifiers in shell scripts. Show readable names, capacity and
availability; store stable identities underneath. Preview the selected choices,
validate prerequisites, and report what failed and how to return to setup.
Success means the operation was verified, not merely that a config file was saved.
