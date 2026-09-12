# Future Crash + LOOK 1.9.3

Global find is responsive again.

The 1.9.0 LOOK-native global finder built the complete home-directory catalog before entering its interactive filter, which introduced a visible multi-second dead period on larger homes.

`f` and `fznv` now return to the better streaming architecture: `fd` (or portable `find`) produces paths continuously while fzf is already accepting input. The finder is styled to LOOK's visual language and exposes fzf's live spinner/match information during enumeration.

`f` hands the chosen result into LOOK for the normal preview/action workflow. `fznv` opens it directly in Neovim.

LOOK is 3.13.3. Future Crash remains 1.1.7.
