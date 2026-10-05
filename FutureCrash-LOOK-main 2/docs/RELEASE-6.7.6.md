# Future Crash + LOOK 6.7.6 · CANONICAL EDGE

Weather place canonicalization is now deterministic and node-independent. Casual US place forms such as `portland oregon` and `portland or` are normalized by LOOK to `Portland, Oregon` before any geocoder call, including model-issued WEATHER tool calls. This removes model phrasing as an accidental dependency of live-edge success.

The practical invariant is: the same semantic location must enter the same information edge on every Fabric node.
