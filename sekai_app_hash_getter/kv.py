import requests
from typing import Optional


class CloudflareKV:
    api_key: str

    def __init__(self, account_id: str, api_key: str) -> None:
        self.account_id = account_id
        self.api_key = api_key

    def write(
        self, namespace_id: str, key_name: str, value: str, metadata: str
    ) -> object:
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{namespace_id}/values/{key_name}"
        req = requests.put(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            files={"metadata": (None, metadata), "value": (None, value)},
        )
        if req.status_code != 200:
            req.raise_for_status()
        return req.json()

    def get(self, namespace_id: str, key_name: str) -> Optional[None]:
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/storage/kv/namespaces/{namespace_id}/values/{key_name}"
        req = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        if req.status_code == 404:
            return None
        else:
            req.raise_for_status()
        return req.json()
