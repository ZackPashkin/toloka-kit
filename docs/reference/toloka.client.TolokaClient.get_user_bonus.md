# get_user_bonus
`toloka.client.TolokaClient.get_user_bonus`

```
get_user_bonus(self, user_bonus_id: str)
```

Reads one specific user bonus

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`user_bonus_id`|**str**|<p>ID of the user bonus.</p>

* **Returns:**

  The user bonus.

* **Return type:**

  [UserBonus](toloka.client.user_bonus.UserBonus.md)

**Examples:**

```python
toloka_client.get_user_bonus(user_bonus_id='1')
```
