BASELINE_GROUNDED_ANSWER_PREFIX = (
    "I found relevant knowledge-base context. Here is a grounded baseline answer:"
)

NO_CONTEXT_MESSAGE = (
    "I do not have enough permitted knowledge-base context to answer this. "
    "Try rephrasing the question or using a role with access to the relevant documents."
)

UNSUPPORTED_TOOL_MESSAGE = (
    "This request needs an agent tool that is not implemented in the current phase yet."
)
