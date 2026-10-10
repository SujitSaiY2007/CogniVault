# Grounding, Citation Integrity, and Abstention

## Contract
In grounded mode, responses must be supported by retrieved, addressable course evidence. Insufficient/unresolvable evidence must lead to abstention or an explicit error.

## Sequence
Retrieve → assess relevance/sufficiency → resolve stored evidence IDs → generate within grounded contract → verify as implemented → display answer and citations distinctly.

## Fail-closed cases
No relevant evidence; insufficient support; missing citation mapping; unresolved conflict; verification failure; retrieval/provider failure.

## Citation rule
Page, slide, timestamp, figure and source IDs must come from stored metadata. Never invent locators or cite a source merely because it ranks highly.

## Honest claim
The project does not guarantee zero hallucinations. It implements or intends evidence-first controls designed to reject/flag unsupported responses; claims must match measured test scope.

## UI
Clearly distinguish grounded answers, citations, abstentions and service errors. The dashboard redesign must not change the backend grounding policy.
