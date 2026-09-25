# Future Crash + LOOK 6.1.13 — Transactional Node Upgrade

Unified Node upgrades now stop the managed resident before replacing its Python source, retire only known user-owned legacy node interpreters, prove localhost :7332 is free, then install and start one managed node. The installer verifies both `fcl-node --version` and the live `/v1/health` version before completing. This closes the race that could leave a 6.1.8 interpreter serving Dash after newer files had been installed.
