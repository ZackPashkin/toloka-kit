# Gender
`toloka.client.filter.Gender`

```
Gender(
    self,
    operator: IdentityOperator,
    value: Union[Gender, str]
)
```

Use to select users by gender.

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`operator`|**[IdentityOperator](toloka.client.primitives.operators.IdentityOperator.md)**|<p>Comparison operator in the condition. For example, for a condition &quot;The user must be 18 years old or older» used date of birth and operator GTE («Greater than or equal»). Possible key values operator depends on the data type in the field value</p>
`value`|**[Gender](toloka.client.filter.Gender.Gender.md)**|<p>User gender.</p>
