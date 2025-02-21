# ApiError
`toloka.client.exceptions.ApiError`

```
ApiError(
    self,
    *,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
    code: Optional[str] = None,
    message: Optional[str] = None,
    payload: Optional[Any] = None
)
```

Error returned from the API Call.

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`status_code`|**Optional\[int\]**|<p>response status code.</p>
`request_id`|**Optional\[str\]**|<p>request ID</p>
`code`|**Optional\[str\]**|<p>error code string</p>
`message`|**Optional\[str\]**|<p>error message</p>
`payload`|**Optional\[Any\]**|<p>additional payload</p>
