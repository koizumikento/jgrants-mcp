import httpx
import pytest
import respx

from jgrants_mcp import get_subsidy_detail, search_subsidies
from jgrants_mcp.client import API_BASE_URL_V1, API_BASE_URL_V2

SEARCH_RESPONSE = {
    "metadata": {"resultset": {"count": 1}},
    "result": [
        {
            "id": "a0WJ200000CDXvUMAX",
            "name": "S-00008317",
            "title": "令和８年度東京都医療ＤＸ人材育成支援事業",
            "subsidy_max_limit": 500000,
            "target_area_search": "東京都",
            "target_number_of_employees": "従業員数の制約なし",
            "acceptance_start_datetime": "2026-04-14T15:00:00.000Z",
            "acceptance_end_datetime": "2026-11-30T14:59:00.000Z",
        }
    ],
}

DETAIL_V2_RESPONSE = {
    "metadata": {"resultset": {"count": 1}},
    "result": [
        {
            "id": "a0WJ200000CDXvUMAX",
            "title": "令和８年度東京都医療ＤＸ人材育成支援事業",
            "institution_name": "東京都",
            "subsidy_catch_phrase": None,
            "outline_of_grant": [],
            "detail": "<p>事業の<strong>目的</strong>です。</p><p>次の段落。</p>",
            "use_purpose": "人材育成を行いたい",
            "industry": "医療、福祉",
            "target_number_of_employees": "従業員数の制約なし",
            "subsidy_max_limit": 500000,
            "subsidy_rate": "10分の10",
            "front_subsidy_detail_page_url": (
                "https://www.jgrants-portal.go.jp/subsidy/a0WJ200000CDXvUMAX"
            ),
            "workflow": [
                {
                    "id": "a0XJ2000006il9OMAQ",
                    "target_area_search": "東京都",
                    "target_area_detail": None,
                    "fiscal_year_round": None,
                    "acceptance_start_datetime": "2026-04-14T15:00Z",
                    "acceptance_end_datetime": "2026-11-30T14:59Z",
                    "project_end_deadline": "2027-03-31T15:00Z",
                }
            ],
            "application_guidelines": [
                {"file_name": "kouho.pdf", "file_content": "QUJD" * 200}
            ],
            "application_form": [],
        }
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_search_subsidies() -> None:
    route = respx.get(f"{API_BASE_URL_V1}/subsidies").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    result = await search_subsidies("医療", acceptance=1)
    assert result["count"] == 1
    item = result["items"][0]
    assert item["id"] == "a0WJ200000CDXvUMAX"
    assert item["title"] == "令和８年度東京都医療ＤＸ人材育成支援事業"
    assert item["subsidy_max_limit"] == 500000
    assert item["acceptance_end_datetime"] == "2026-11-30T14:59:00.000Z"
    params = route.calls.last.request.url.params
    assert params["keyword"] == "医療"
    assert params["sort"] == "acceptance_end_datetime"
    assert params["order"] == "ASC"
    assert params["acceptance"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_search_subsidies_with_filters() -> None:
    route = respx.get(f"{API_BASE_URL_V1}/subsidies").mock(
        return_value=httpx.Response(200, json={"metadata": {}, "result": []})
    )
    result = await search_subsidies(
        "省エネ", acceptance=0, target_area_search="東京都", industry="製造業"
    )
    assert result["count"] == 0
    params = route.calls.last.request.url.params
    assert params["acceptance"] == "0"
    assert params["target_area_search"] == "東京都"
    assert params["industry"] == "製造業"


@pytest.mark.asyncio
async def test_search_subsidies_rejects_short_keyword() -> None:
    with pytest.raises(ValueError):
        await search_subsidies("あ")


@pytest.mark.asyncio
@respx.mock
async def test_search_subsidies_api_error() -> None:
    respx.get(f"{API_BASE_URL_V1}/subsidies").mock(
        return_value=httpx.Response(400, text="Bad request")
    )
    with pytest.raises(ValueError, match="400"):
        await search_subsidies("省エネ")


@pytest.mark.asyncio
@respx.mock
async def test_get_subsidy_detail_v2() -> None:
    respx.get(f"{API_BASE_URL_V2}/subsidies/id/a0WJ200000CDXvUMAX").mock(
        return_value=httpx.Response(200, json=DETAIL_V2_RESPONSE)
    )
    result = await get_subsidy_detail("a0WJ200000CDXvUMAX")
    assert result["title"] == "令和８年度東京都医療ＤＸ人材育成支援事業"
    assert result["subsidy_rate"] == "10分の10"
    assert result["detail"] == "事業の目的です。\n次の段落。"
    workflow = result["workflow"][0]
    assert workflow["target_area_search"] == "東京都"
    assert workflow["acceptance_end_datetime"] == "2026-11-30T14:59Z"
    assert workflow["project_end_deadline"] == "2027-03-31T15:00Z"
    guideline = result["application_guidelines"][0]
    assert guideline["file_name"] == "kouho.pdf"
    assert guideline["file_content"] == {"base64_length": 800, "omitted": True}


@pytest.mark.asyncio
@respx.mock
async def test_get_subsidy_detail_not_found() -> None:
    respx.get(f"{API_BASE_URL_V2}/subsidies/id/a0WJ200000XXXXXX").mock(
        return_value=httpx.Response(200, json={"metadata": {}, "result": []})
    )
    with pytest.raises(ValueError, match="No subsidy found"):
        await get_subsidy_detail("a0WJ200000XXXXXX")
