# get_assignment
`toloka.client.TolokaClient.get_assignment`

```
get_assignment(self, assignment_id: str)
```

Reads one specific assignment

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`assignment_id`|**str**|<p>ID of assignment.</p>

* **Returns:**

  The solution read as a result.

* **Return type:**

  [Assignment](toloka.client.assignment.Assignment.md)

**Examples:**

```python
toloka_client.get_assignment(assignment_id='1')
```
