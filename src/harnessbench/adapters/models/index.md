# Model Adapters

Normalize model invocation metadata and responses. Record provider/model revisions and relevant inference settings.

- `base.py`: model adapter protocol and response value object.
- `fixture.py`: deterministic baseline adapter that replays a recorded response.
- `openai_compatible.py`: OpenAI-compatible chat-completions adapter with environment-supplied credentials.
