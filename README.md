# jgrants-mcp

デジタル庁の補助金電子申請システム「Jグランツ」の公開APIから、国や自治体の補助金を検索し、公募の詳細（対象条件・補助率・上限額・募集期間・公募要領）を取得できます。申請や採択実績の取得はできません（読み取り専用）。

[MCP登録](#mcpクライアントに登録する) · [CLI](#cliで使う) · [Pythonライブラリ](#pythonライブラリとして使う)

## 利用前に

[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。APIキーの設定は不要です（公開APIを認証なしで呼びます）。

## MCPクライアントに登録する

公開GitHubリポジトリから `uvx` で起動します。初回は依存関係の準備に時間がかかることがあります。

### Codex

```sh
codex mcp add jgrants-mcp -- uvx --python 3.12 --from git+https://github.com/koizumikento/jgrants-mcp.git@main jgrants-mcp
codex mcp list
```

`codex mcp list` で登録を確認し、Codexの新しいセッションで `/mcp` を開くと、接続状態を確認できます。[Codexの公式設定ガイド](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

Codexのデスクトップアプリでは、設定の「MCP servers」でSTDIOサーバーを追加し、下のJSON例と同じコマンド・引数を指定する方法もあります。

### Claude Desktop / Cursor

次のファイルに設定します。

- Claude Desktop（Windows） `%APPDATA%/Claude/claude_desktop_config.json`
- Claude Desktop（macOS） `~/Library/Application Support/Claude/claude_desktop_config.json`
- Cursor `.cursor/mcp.json`（プロジェクト内）

既に `mcpServers` がある場合は、その中にサーバーの項目を追加してください。保存後にクライアントを再起動し、ツールが表示されるか確認します。[設定ファイルの場所と接続手順](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)

```json
{
  "mcpServers": {
    "jgrants-mcp": {
      "command": "uvx",
      "args": [
        "--python",
        "3.12",
        "--from",
        "git+https://github.com/koizumikento/jgrants-mcp.git@main",
        "jgrants-mcp"
      ]
    }
  }
}
```

`uvx` が見つからない場合は、設定のコマンドに実行ファイルの絶対パスを指定してください。

登録後は、チャットで次のように聞けます。

> 東京都で受付中の、人材育成に使える補助金を探して。

> 「省エネ」で検索して、締切が近い順に並べて。

## ツール

### `search_subsidies`

補助金をキーワードで検索します。一覧の検索はAPIの仕様でキーワード（2文字以上）が必須で、キーワードなしの全件取得はできません。ページ送りはなく、条件に合う全件が1回で返ります。

| 引数 | 必須 | 内容 |
| --- | --- | --- |
| `keyword` | ○ | 検索キーワード（2〜255文字） |
| `sort` | | `created_date` / `acceptance_start_datetime` / `acceptance_end_datetime`（既定） |
| `order` | | `ASC`（既定） / `DESC` |
| `acceptance` | | `1`（既定）= 受付中のみ / `0` = 受付前・終了分も含む |
| `industry` | | 業種での絞り込み（APIの定義値） |
| `use_purpose` | | 利用目的での絞り込み（APIの定義値） |
| `target_number_of_employees` | | 従業員数の条件（APIの定義値） |
| `target_area_search` | | 補助対象地域（例: 東京都） |

返却値には件数と、各補助金のID・タイトル・補助上限額・対象地域・従業員数の条件・受付開始／終了日時が入ります。

### `get_subsidy_detail`

補助金IDを指定して詳細を1件取得します。

| 引数 | 必須 | 内容 |
| --- | --- | --- |
| `subsidy_id` | ○ | `search_subsidies` が返したID（18文字以下） |
| `version` | | `v2`（既定） / `v1` |

返却値には、制度名、概要、公募要領の本文（HTMLをプレーンテキスト化したもの）、利用目的、対象業種、従業員数の条件、補助上限額、補助率、公式ページのURL、募集の回（workflow）ごとの対象地域・受付期間・事業終了期限が入ります。V2では地域と期間が回ごとに分かれ、V1では公募直下の値を workflow 1件に正規化して返します。添付ファイル（公募要領・申請様式）は本体（Base64）を返さず、ファイル名などのメタデータのみを返します。

## CLIで使う

```sh
# 受付中の補助金を締切が近い順に検索
uvx --from git+https://github.com/koizumikento/jgrants-mcp.git@main jgrants-mcp search-subsidies --keyword 省エネ --acceptance 1

# 地域で絞る（受付前・終了分も含む）
uvx --from git+https://github.com/koizumikento/jgrants-mcp.git@main jgrants-mcp search-subsidies --keyword DX --acceptance 0 --target-area-search 東京都

# 詳細を1件取得
uvx --from git+https://github.com/koizumikento/jgrants-mcp.git@main jgrants-mcp get-subsidy-detail --subsidy-id a0WJ200000CDXvUMAX
```

引数なしで起動するとMCPサーバー（stdio）として動作します。`serve` を付けても同じです。

## Pythonライブラリとして使う

```python
import asyncio

from jgrants_mcp import get_subsidy_detail, search_subsidies


async def main() -> None:
    result = await search_subsidies("省エネ", acceptance=1)
    for item in result["items"]:
        print(item["id"], item["title"], item["acceptance_end_datetime"])
    detail = await get_subsidy_detail(result["items"][0]["id"])
    print(detail["subsidy_rate"], detail["workflow"])


asyncio.run(main())
```

## データについて

- 出典はデジタル庁が運営する [Jグランツ](https://www.jgrants-portal.go.jp/) の公開APIです。仕様は [JグランツAPIドキュメント](https://developers.digital.go.jp/documents/jgrants/api/) にあります。利用にあたっては [JGrants Web-API 利用規約](https://www.jgrants-portal.go.jp/open-api) に従ってください。API利用概要では呼び出し上限は10回／1秒とされています。
- 返るのは補助金制度の情報のみで、申請した会社や採択された会社の情報は含まれません。採択実績は gBizINFO 側の情報です。
- JGrantsに登録された公募だけが対象です。受付開始前の公募も `acceptance=0` で引けますが、各省庁の概算要求や予算案の段階にある事業は載りません。
- 日時はAPIの返却値（UTC）のまま返します。日本時間への変換は利用側で行ってください。
- キーワード検索の絞り込みは粗く、無関係な公募が混ざることがあります。タイトル・対象地域・業種で選別して使ってください。
- デジタル庁公式のMCPサーバー（digital-go-jp/jgrants-mcp-server）は技術検証目的のサンプルコードと位置づけられているため、本リポジトリは公開APIを直接呼ぶ独立実装にしています。エンドポイントとパラメータの確認には公式サンプルのコードを参照しました。

## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```

CIのテストはオフライン（HTTPモック）で動きます。上流APIの契約確認は、実APIへの小さな読み取りサンプルで別途行います。
