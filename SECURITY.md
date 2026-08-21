# Security boundary

This repository contains configuration templates only. Never commit:

- `~/.wx-cli/all_keys.json`, WeChat databases, decrypted caches or extracted attachments;
- Telegram `.session` files, API credentials or exported messages;
- Lark access tokens, profiles, chat exports or Heartbeat memory;
- generated scan output containing private conversations.

`scripts/wx-setup.sh` delegates key discovery to the installed `wx` CLI. It does
not implement key extraction and does not print discovered keys. Run it only on
a machine and WeChat account you control.

The upstream `jackwener/wx-cli` GitHub repository currently returns HTTP 451.
This repository does not mirror its source or binaries. Review your local laws,
organization policy and the installed package before use.
