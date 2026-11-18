import html
import re
from typing import Annotated, Any, Literal

import httpx
from pydantic import StringConstraints, validate_call

API_BASE_URL_V1 = "https://api.jgrants-portal.go.jp/exp/v1/public"
API_BASE_URL_V2 = "https://api.jgrants-portal.go.jp/exp/v2/public"
API_DOC_URL = "https://developers.digital.go.jp/documents/jgrants/api/"
PORTAL_URL = "https://www.jgrants-portal.go.jp/"

Keyword = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
SubsidyId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=18)]
SortField = Literal["created_date", "acceptance_start_datetime", "acceptance_end_datetime"]
Order = Literal["ASC", "DESC"]
Acceptance = Literal[0, 1]
DetailVersion = Literal["v1", "v2"]


async def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise ValueError(
            f"JGrants API returned HTTP {response.status_code}: {response.text[:200]}"
        )
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("JGrants API returned an unexpected response.")
    return data


def _html_to_text(value: Any) -> Any:
    """Flatten an HTML string to plain text; pass other values through."""
    if not isinstance(value, str) or "<" not in value:
        return value
    text = re.sub(r"<br\s*/?>", "\n", value)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _strip_attachment_payloads(value: Any) -> Any:
    """Replace long base64 payloads in attachment entries with their length."""
    if isinstance(value, dict):
        return {key: _strip_attachment_payloads(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_strip_attachment_payloads(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return {"base64_length": len(value), "omitted": True}
    return value


def _search_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "subsidy_max_limit": item.get("subsidy_max_limit"),
        "target_area_search": item.get("target_area_search"),
        "target_number_of_employees": item.get("target_number_of_employees"),
        "acceptance_start_datetime": item.get("acceptance_start_datetime"),
        "acceptance_end_datetime": item.get("acceptance_end_datetime"),
    }


def _detail_item(item: dict[str, Any], version: DetailVersion) -> dict[str, Any]:
    if version == "v2":
        workflow = [
            {
                "target_area_search": entry.get("target_area_search"),
                "target_area_detail": entry.get("target_area_detail"),
                "fiscal_year_round": entry.get("fiscal_year_round"),
                "acceptance_start_datetime": entry.get("acceptance_start_datetime"),
                "acceptance_end_datetime": entry.get("acceptance_end_datetime"),
                "project_end_deadline": entry.get("project_end_deadline"),
            }
            for entry in item.get("workflow") or []
        ]
    else:
        workflow = [
            {
                "target_area_search": item.get("target_area_search"),
                "target_area_detail": None,
                "fiscal_year_round": None,
                "acceptance_start_datetime": item.get("acceptance_start_datetime"),
                "acceptance_end_datetime": item.get("acceptance_end_datetime"),
                "project_end_deadline": item.get("project_end_deadline"),
            }
        ]
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "institution_name": item.get("institution_name"),
        "subsidy_catch_phrase": item.get("subsidy_catch_phrase"),
        "outline_of_grant": item.get("outline_of_grant"),
        "detail": _html_to_text(item.get("detail")),
        "use_purpose": item.get("use_purpose"),
        "industry": item.get("industry") or item.get("target_industry"),
        "target_number_of_employees": item.get("target_number_of_employees"),
        "subsidy_max_limit": item.get("subsidy_max_limit"),
        "subsidy_rate": item.get("subsidy_rate"),
        "front_subsidy_detail_page_url": item.get("front_subsidy_detail_page_url"),
        "workflow": workflow,
        "application_guidelines": _strip_attachment_payloads(item.get("application_guidelines")),
        "application_form": _strip_attachment_payloads(item.get("application_form")),
    }


@validate_call
async def search_subsidies(
    keyword: Keyword,
    sort: SortField = "acceptance_end_datetime",
    order: Order = "ASC",
    acceptance: Acceptance = 1,
    industry: str | None = None,
    use_purpose: str | None = None,
    target_number_of_employees: str | None = None,
    target_area_search: str | None = None,
) -> dict[str, Any]:
    """JGrantsに登録された補助金をキーワードで検索する。

    返るのは制度の情報（補助金名・対象地域・従業員数の条件・補助上限額・
    受付期間）で、申請者や採択企業の情報は含まれない。キーワード検索の
    絞り込みは粗く、無関係な公募が混ざることがある。受付期間の日時は
    UTC（APIの返却値そのまま）。

    Args:
        keyword: 検索キーワード（2文字以上255文字以下、必須）。
        sort: 並べ替え項目。created_date / acceptance_start_datetime /
            acceptance_end_datetime。
        order: ASC（昇順）または DESC（降順）。
        acceptance: 1 は受付中のみ、0 は受付前・終了分も含む全て。
        industry: 業種での絞り込み（APIの定義値）。
        use_purpose: 利用目的での絞り込み（APIの定義値）。
        target_number_of_employees: 従業員数の条件（APIの定義値）。
        target_area_search: 補助対象地域での絞り込み（例: 東京都）。
    """
    params: dict[str, Any] = {
        "keyword": keyword,
        "sort": sort,
        "order": order,
        "acceptance": acceptance,
    }
    if industry is not None:
        params["industry"] = industry
    if use_purpose is not None:
        params["use_purpose"] = use_purpose
    if target_number_of_employees is not None:
        params["target_number_of_employees"] = target_number_of_employees
    if target_area_search is not None:
        params["target_area_search"] = target_area_search
    data = await _get_json(f"{API_BASE_URL_V1}/subsidies", params=params)
    results = data.get("result") or []
    return {
        "count": len(results),
        "items": [_search_item(item) for item in results],
        "source_url": API_DOC_URL,
    }


@validate_call
async def get_subsidy_detail(
    subsidy_id: SubsidyId,
    version: DetailVersion = "v2",
) -> dict[str, Any]:
    """補助金1件の詳細を取得する。

    補助率、利用目的、対象業種、公募要領の本文（HTMLをプレーンテキスト化
    したもの）、募集の回（workflow）ごとの対象地域と受付期間、事業終了
    期限が返る。添付ファイル（公募要領・申請様式）は本体（Base64）を
    省略し、ファイル名などのメタデータだけを返す。日時はUTC。

    Args:
        subsidy_id: search_subsidies が返した補助金ID（18文字以下）。
        version: 詳細APIの版。v2 は募集の回ごとに地域と期間を持つ形で、
            既定はこちら。v1 は地域と期間が公募直下にある旧形式で、
            workflow 1件に正規化して返す。
    """
    base = API_BASE_URL_V2 if version == "v2" else API_BASE_URL_V1
    data = await _get_json(f"{base}/subsidies/id/{subsidy_id}")
    result = data.get("result") or []
    if isinstance(result, dict):
        result = [result]
    if not result:
        raise ValueError(f"No subsidy found for id: {subsidy_id}")
    return {
        **_detail_item(result[0], version),
        "source_url": PORTAL_URL,
    }
