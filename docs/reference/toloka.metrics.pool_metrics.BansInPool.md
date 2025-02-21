# BansInPool
`toloka.metrics.pool_metrics.BansInPool`

```
BansInPool(
    self,
    pool_id: str,
    count_name: Optional[str] = None,
    filter_by_comment: Optional[Dict[str, str]] = None,
    join_events: bool = False,
    *,
    toloka_client: TolokaClient = None,
    timeout: timedelta = ...
)
```

Tracking the new user restrictions in pool


Be careful: if you set in quality controls to ban performers 'on project', bans 'on pool' will never happen.

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`pool_id`|**str**|<p>From which pool track metrics.</p>
`count_name`|**Optional\[str\]**|<p>Metric name for a count of bans.</p>
`filter_by_comment`|**Optional\[Dict\[str, str\]\]**|<p>Allow to split user restriction into several lines based on comment. Dictionary where, key - comment string, and value - name for line in which will be aggregated bans with this comments.</p>
`join_events`|**bool**|<p>Count all events in one point.  Default False.</p>

**Examples:**

How to collect this metrics:
```python
def print_metric(metric_dict):
    print(metric_dict)
collector = MetricCollector([BansInPool(pool_id, toloka_client=toloka_client)], print_metric)
asyncio.run(collector.run())
```

How to split bans onto several metrics.
```python
collector = MetricCollector(
    [
        BansInPool(
            pool_id,
            toloka_client=toloka_client,
            filter_by_comment={'fast answers': 'fast', 'bad quality on honeypots': 'honeypots'}
        ),
    ],
    print_metric
)
asyncio.run(collector.run())
```
## Methods summary

| Method | Description |
| :------| :-----------|
[get_line_names](toloka.metrics.pool_metrics.BansInPool.get_line_names.md)| Returns a list of metric names that can be generated by this class instance.
