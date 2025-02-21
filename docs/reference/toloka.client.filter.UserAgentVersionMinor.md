# UserAgentVersionMinor
`toloka.client.filter.UserAgentVersionMinor`

```
UserAgentVersionMinor(
    self,
    operator: CompareOperator,
    value: Optional[int] = None
)
```

Use to select users by minor browser version.

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`operator`|**[CompareOperator](toloka.client.primitives.operators.CompareOperator.md)**|<p>Comparison operator in the condition. For example, for a condition &quot;The user must be 18 years old or older» used date of birth and operator GTE («Greater than or equal»). Possible key values operator depends on the data type in the field value</p>
`value`|**Optional\[int\]**|<p>Minor browser version.</p>
