# add_action
`toloka.client.quality_control.QualityControl.add_action`

```
add_action(
    self,
    collector: CollectorConfig,
    action: RuleAction,
    conditions: List[RuleCondition]
)
```

Adds new QualityControlConfig to QualityControl object. Usually in pool.


See example in QualityControl class.

Arg:
    collector: Parameters for collecting statistics (for example, the number of task skips in the pool).
    action: Action if conditions are met (for example, close access to the project).
    conditions: Conditions (for example, skipping 10 sets of tasks in a row).

