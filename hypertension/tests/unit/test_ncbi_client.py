import pytest
from unittest.mock import MagicMock, patch

import httpx

from hypertensiondb.ingest.ncbi_client import NCBIClient


_ESEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
  <Count>3</Count>
  <RetMax>3</RetMax>
  <IdList>
    <Id>39111111</Id>
    <Id>39222222</Id>
    <Id>39333333</Id>
  </IdList>
</eSearchResult>"""


_EFETCH_PUBMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>39111111</PMID>
      <Article>
        <Journal>
          <Title>J Hypertens</Title>
        </Journal>
        <ArticleTitle>Test RCT on hypertension</ArticleTitle>
        <Abstract>
          <AbstractText>We studied combination therapy.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
        </AuthorList>
      </Article>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName>Hypertension</DescriptorName>
        </MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">39111111</ArticleId>
        <ArticleId IdType="doi">10.1234/test</ArticleId>
        <ArticleId IdType="pmc">PMC9999999</ArticleId>
      </ArticleIdList>
      <History>
        <PubMedPubDate PubStatus="pubmed">
          <Year>2026</Year><Month>1</Month><Day>15</Day>
        </PubMedPubDate>
      </History>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


@pytest.fixture
def mock_http():
    with patch("hypertensiondb.ingest.ncbi_client.httpx.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value.__enter__.return_value = instance
        yield instance


@pytest.mark.unit
def test_esearch_returns_id_list(mock_http):
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = _ESEARCH_XML
    mock_http.get.return_value = mock_resp

    client = NCBIClient()
    ids = client.esearch(query="hypertension", db="pubmed", retmax=10)
    assert ids == ["39111111", "39222222", "39333333"]
    args, kwargs = mock_http.get.call_args
    assert "esearch" in args[0]
    assert kwargs["params"]["term"] == "hypertension"
    assert kwargs["params"]["db"] == "pubmed"
    assert kwargs["params"]["retmax"] == 10


@pytest.mark.unit
def test_esearch_passes_api_key_when_set(mock_http, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "test-key-abc")
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = _ESEARCH_XML
    mock_http.get.return_value = mock_resp

    NCBIClient().esearch(query="x")
    _, kwargs = mock_http.get.call_args
    assert kwargs["params"]["api_key"] == "test-key-abc"


@pytest.mark.unit
def test_esearch_omits_api_key_when_unset(mock_http, monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    mock_resp = MagicMock(status_code=200, text=_ESEARCH_XML)
    mock_http.get.return_value = mock_resp
    NCBIClient().esearch(query="x")
    _, kwargs = mock_http.get.call_args
    assert "api_key" not in kwargs["params"]


@pytest.mark.unit
def test_efetch_pubmed_parses_metadata(mock_http):
    mock_resp = MagicMock(status_code=200, text=_EFETCH_PUBMED_XML)
    mock_http.get.return_value = mock_resp

    records = NCBIClient().efetch_pubmed(["39111111"])
    assert len(records) == 1
    r = records[0]
    assert r["pmid"] == "39111111"
    assert r["doi"] == "10.1234/test"
    assert r["pmc_id"] == "PMC9999999"
    assert r["title"] == "Test RCT on hypertension"
    assert r["abstract"].startswith("We studied")
    assert r["authors"] == ["Smith J"]
    assert r["year"] == 2026
    assert r["journal"] == "J Hypertens"
    assert r["publication_types"] == ["Randomized Controlled Trial"]
    assert r["mesh_terms"] == ["Hypertension"]


@pytest.mark.unit
def test_efetch_pubmed_retries_transient_http_errors(mock_http):
    first = MagicMock(status_code=429, text="rate limited")
    first.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Too Many Requests",
        request=MagicMock(),
        response=first,
    )
    second = MagicMock(status_code=200, text=_EFETCH_PUBMED_XML)
    mock_http.get.side_effect = [first, second]

    client = NCBIClient(max_retries=2, retry_sleep=lambda seconds: None)

    records = client.efetch_pubmed(["39111111"])

    assert records[0]["pmid"] == "39111111"
    assert mock_http.get.call_count == 2


@pytest.mark.unit
def test_efetch_pubmed_error_includes_endpoint_context(mock_http):
    response = MagicMock(status_code=500, text="server error")
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error",
        request=MagicMock(),
        response=response,
    )
    mock_http.get.return_value = response

    client = NCBIClient(max_retries=1, retry_sleep=lambda seconds: None)

    with pytest.raises(RuntimeError, match="NCBI efetch pubmed failed"):
        client.efetch_pubmed(["39111111"])


@pytest.mark.unit
def test_efetch_pmc_xml_returns_raw(mock_http):
    fake_jats = "<?xml version='1.0'?><article><body/></article>"
    mock_resp = MagicMock(status_code=200, text=fake_jats)
    mock_http.get.return_value = mock_resp

    xml = NCBIClient().efetch_pmc_xml("PMC9999999")
    assert xml == fake_jats
    _, kwargs = mock_http.get.call_args
    assert kwargs["params"]["db"] == "pmc"
    assert kwargs["params"]["id"] == "9999999"
    assert kwargs["params"]["rettype"] == "xml"


@pytest.mark.unit
def test_http_error_raises(mock_http):
    mock_resp = MagicMock(status_code=503)
    mock_resp.raise_for_status.side_effect = Exception("503 Server Error")
    mock_http.get.return_value = mock_resp
    with pytest.raises(Exception):
        NCBIClient().esearch(query="x")
@pytest.mark.unit
def test_ncbi_client_params_include_email(monkeypatch):
    monkeypatch.setenv("NCBI_EMAIL", "user@example.com")
    monkeypatch.delenv("PUBMED_EMAIL", raising=False)
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    client = NCBIClient()

    assert client._params(db="pubmed") == {
        "db": "pubmed",
        "email": "user@example.com",
    }


@pytest.mark.unit
def test_ncbi_client_params_accept_pubmed_email_fallback(monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    monkeypatch.setenv("PUBMED_EMAIL", "fallback@example.com")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    client = NCBIClient()

    assert client._params(db="pubmed") == {
        "db": "pubmed",
        "email": "fallback@example.com",
    }
