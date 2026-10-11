# Product setup

Future Crash + LOOK must work for a fresh person, OS account and Fabric.

- Keep developer usernames, machine names, network addresses, drive UUIDs and
  private preferences in local user configuration. Never make them operational
  defaults or ship them in active scheduling templates.
- Derive choices from the current user's environment and trusted peers. Do not
  inherit another account's identities, authorization, credentials or settings.
- Make setup discoverable through Settings, command help and useful empty states.
  Explain what a feature does and what it protects before asking for choices.
- Discover connected hardware when the user opens setup. Plugging something in
  must not silently initialize, authorize, format or launch a setup flow.
- Hide incidental complexity such as mount paths and UUID entry behind readable
  resource choices, while retaining stable identifiers underneath.
- Show a concrete summary before setup makes changes. Report failures with a
  next step; only claim success after the operation is verified.
- Preserve existing user configuration and schedules during upgrades. Test fresh
  accounts as well as the developer's installation.

See [Setup principles](docs/SETUP-PRINCIPLES.md) and
[Backup onboarding](docs/FABRIC-RECOVERY.md).
