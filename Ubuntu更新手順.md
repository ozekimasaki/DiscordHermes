# Ubuntu 上でファイルを更新する方法

このドキュメントは、**Ubuntu 上でこのリポジトリのファイルを更新する方法**をまとめたものです。

対象は、たとえば次のようなケースです。

- Ubuntu 上に clone 済みの repo を最新化したい
- 手元の PC で直したファイルを Ubuntu に送りたい
- Ubuntu 上で直接ファイルを編集したい
- 更新後に Hermes 側へ反映したい

## 1. いちばん安全な方法: `git pull` で更新する

Ubuntu 上にこの repo が clone 済みなら、まずはこの方法が基本です。

```bash
cd ~/hermes-discord-admin-extension
git status
git pull --ff-only
```

### ローカル変更がある場合

`git status` で変更が出ている場合は、そのまま `git pull` すると競合することがあります。

安全に進めるなら、次のどれかにしてください。

```bash
git add .
git commit -m "WIP: local changes"
git pull --ff-only
```

または一時退避します。

```bash
git stash push -u
git pull --ff-only
git stash pop
```

## 2. 手元の PC から Ubuntu にファイルを送る

Git を使わず、**特定のファイルだけ** Ubuntu に送りたい場合は `scp` が簡単です。

例: `README.md` を送る

```bash
scp README.md <ubuntu-user>@<ubuntu-host>:~/hermes-discord-admin-extension/README.md
```

ディレクトリごと送りたい場合は `rsync` が便利です。

```bash
rsync -avz ./extensions/ <ubuntu-user>@<ubuntu-host>:~/hermes-discord-admin-extension/extensions/
```

差分だけ送りたいときも `rsync` が向いています。

## 3. Ubuntu 上で直接編集する

Ubuntu にログインして、その場で編集する方法です。

```bash
cd ~/hermes-discord-admin-extension
nano README.md
```

`vim` を使うなら:

```bash
vim README.md
```

編集後は、必要なら `git diff` で確認します。

```bash
git --no-pager diff
```

## 4. この repo の更新を Hermes 側へ反映する

この repo は **Hermes 本体を直接書き換える構成ではなく**、`~/.hermes` 側へ skill や config snippet を入れる構成です。

そのため、**repo を更新しただけでは Hermes 側に反映されないことがあります。**

更新後は、必要に応じて次を実行してください。

```bash
cd ~/hermes-discord-admin-extension
python3 scripts/install_extension.py --hermes-home ~/.hermes
```

このスクリプトは主に次を更新します。

- `~/.hermes/skills/server-admin`
- `~/.hermes/discord-admin.env.example`
- `~/.hermes/discord-admin.config.snippet.yaml`

## 5. `config.yaml` への反映が必要か確認する

MCP の公開ツールや launcher path が変わった場合は、生成された snippet を見直してください。

```bash
cat ~/.hermes/discord-admin.config.snippet.yaml
```

必要なら、その内容を `~/.hermes/config.yaml` にマージします。

この repo の方針として、**Discord token は `config.yaml` ではなく `~/.hermes/.env` に置きます。**

## 6. `.env` やシェル設定を変えた場合

`~/.bashrc` や `~/.zshrc` を更新した場合は、シェルを再読み込みします。

```bash
source ~/.bashrc
```

`~/.hermes/.env` を編集した場合は、Hermes の再起動が必要になることがあります。

## 7. 更新後の確認

まず repo 側のテストを流します。

```bash
cd ~/hermes-discord-admin-extension
python3 -m unittest discover -s tests -v
```

次に、Hermes 側の状態を必要に応じて確認します。

```bash
hermes gateway status
```

service 化している場合は再起動します。

```bash
hermes gateway restart
```

`restart` が使いにくい環境では、`stop` → `start` でも構いません。

## 8. よくある更新パターン

### パターン A: GitHub の最新を Ubuntu に入れる

```bash
cd ~/hermes-discord-admin-extension
git pull --ff-only
python3 scripts/install_extension.py --hermes-home ~/.hermes
python3 -m unittest discover -s tests -v
hermes gateway restart
```

### パターン B: 手元で直したファイルだけ Ubuntu に送る

```bash
scp extensions/mcp/discord_admin_server/tool_registry.py <ubuntu-user>@<ubuntu-host>:~/hermes-discord-admin-extension/extensions/mcp/discord_admin_server/tool_registry.py
```

送ったあとに反映:

```bash
ssh <ubuntu-user>@<ubuntu-host>
cd ~/hermes-discord-admin-extension
python3 scripts/install_extension.py --hermes-home ~/.hermes
python3 -m unittest discover -s tests -v
hermes gateway restart
```

### パターン C: Ubuntu 上で直接編集してそのまま反映

```bash
cd ~/hermes-discord-admin-extension
nano extensions/skills/server-admin/SKILL.md
python3 scripts/install_extension.py --hermes-home ~/.hermes
python3 -m unittest discover -s tests -v
hermes gateway restart
```

## 9. どの手順が必要かの目安

- **repo のコードだけ更新**: `git pull` または `scp/rsync`
- **skill / config snippet を更新**: `python3 scripts/install_extension.py --hermes-home ~/.hermes`
- **`.env` や起動設定を更新**: Hermes の再起動
- **シェル設定を更新**: `source ~/.bashrc`

## 10. 補足

Hermes をすでに導入済みなら、通常は **`bootstrap_rpi.py` を毎回やり直す必要はありません**。

日常的な更新では、ほとんどの場合次の 4 ステップで十分です。

```bash
cd ~/hermes-discord-admin-extension
git pull --ff-only
python3 scripts/install_extension.py --hermes-home ~/.hermes
hermes gateway restart
```
