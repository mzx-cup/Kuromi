"""S7 supervision package — L3 supervision layer (rule engine + DSL).

This package hosts:
  - ``dsl`` — safe-AST trigger DSL parser/evaluator
  - ``rule_engine`` — hourly rule evaluation + event creation
  - ``channel_dispatcher`` — escalation-chain channel fan-out (in-app / push / email)
  - ``seeder`` — one-shot port of the legacy 27-rule ProactiveAdvisor

Models live in ``app.models.supervision`` and ORM repositories in
``app.repositories.orm.supervision``.
"""
