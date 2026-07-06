"""Skywatcher tool layer.

These are the deterministic, testable functions the agents call.
Keeping them separate from the LLM layer means we can unit-test the
orbital math without any API key.
"""
