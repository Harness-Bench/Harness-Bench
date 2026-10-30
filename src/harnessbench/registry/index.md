# Registry

Loads and validates versioned task and benchmark definitions. Does not execute tasks or score outcomes.

- `loader.py`: reads task JSON and validates it against `schemas/task.schema.json`.
- `experiment_loader.py`: reads experiment JSON and validates it against `schemas/experiment.schema.json`.
