"""
Experiment harness for the BitTorrent engine.

Contains a controlled-localhost swarm (mock tracker + mock peers) used
for two purposes:
  - run_comparison.py: rarest-first vs random A/B measurements.
  - tests/test_e2e_peer.py: end-to-end peer-wire-protocol integration test.

The mock swarm is deterministic and contained: it does not touch the
network outside loopback.
"""
