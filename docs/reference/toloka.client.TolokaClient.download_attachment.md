# download_attachment
`toloka.client.TolokaClient.download_attachment`

```
download_attachment(
    self,
    attachment_id: str,
    out: BinaryIO
)
```

Downloads specific attachment

## Parameters Description

| Parameters | Type | Description |
| :----------| :----| :-----------|
`attachment_id`|**str**|<p>ID of attachment.</p>
`out`|**BinaryIO**|<p>File object where to put downloaded file.</p>

**Examples:**

How to download an attachment.

```python
with open('my_new_file.txt', 'wb') as out_f:
    toloka_client.download_attachment(attachment_id='1', out=out_f)
```
