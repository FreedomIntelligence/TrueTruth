import os
from pathlib import Path

import typer


def _load_dotenv(env_path: Path) -> None:
    """Load .env into os.environ without overwriting existing shell variables."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


# Load .env from the project root (where hdb is invoked, i.e. hypertension/)
_load_dotenv(Path.cwd() / ".env")
from hypertensiondb import __version__
from hypertensiondb.ingest.ncbi_client import NCBIClient

app = typer.Typer(help="Hypertension Evidence DB CLI")

EVIDENCE_ROOT = Path("evidence")
COLLECTION_NAME = "hypertension_evidence"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    """hdb: Hypertension Evidence DB command line."""


ingest_app = typer.Typer(help="Ingest evidence from PDF / API / manual")
index_app = typer.Typer(help="Manage Qdrant index")
lint_app = typer.Typer(help="Data quality checks")

app.add_typer(ingest_app, name="ingest")
app.add_typer(index_app, name="index")
app.add_typer(lint_app, name="lint")


@ingest_app.command("dry-run")
def ingest_dry_run(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    evidence_type: str = typer.Option("RCT", "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Run ingest pipeline without writing — print preview."""
    pipeline = _build_ingest_pipeline()
    result = pipeline.ingest_pdf(pdf_path, evidence_type=evidence_type, dry_run=True)
    typer.echo(f"Status: {result.status.value}")
    if result.frontmatter:
        typer.echo("--- frontmatter ---")
        import yaml as _yaml
        typer.echo(_yaml.safe_dump(result.frontmatter, allow_unicode=True, sort_keys=False))
    if result.sections:
        typer.echo("--- sections (non-empty keys) ---")
        for k, v in result.sections.items():
            if v.strip():
                typer.echo(f"  {k}: {v[:80]}{'...' if len(v) > 80 else ''}")
    if result.error:
        typer.echo(f"--- error ---\n{result.error}")


@ingest_app.command("pdf")
def ingest_pdf(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    evidence_type: str = typer.Option(..., "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Full ingest: PDF → parse → clean → section → extract → validate → write."""
    if evidence_type not in {"RCT", "SR", "META", "GL", "TCM"}:
        typer.echo(f"Invalid type: {evidence_type}")
        raise typer.Exit(1)
    pipeline = _build_ingest_pipeline()
    result = pipeline.ingest_pdf(pdf_path, evidence_type=evidence_type)
    if result.status.value == "ok":
        typer.echo(f"OK: written to {result.output_path}")
    elif result.status.value == "quarantined":
        typer.echo(f"QUARANTINED: {result.error}")
        typer.echo(f"  see {result.output_path}")
        raise typer.Exit(2)
    elif result.status.value == "parse_failed":
        typer.echo(f"PARSE_FAILED: {result.error}")
        raise typer.Exit(3)


def _build_ingest_pipeline():
    from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
    from hypertensiondb.ingest.pipeline import IngestPipeline

    evidence_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    raw_root = Path(os.getenv("RAW_ROOT", "raw"))
    failed_root = raw_root / "_failed"

    extractor_name = os.getenv("INGEST_EXTRACTOR", "mock")
    if extractor_name == "openai":
        from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor
        extractor = LLMFrontmatterExtractor(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_EXTRACT_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
    else:
        from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
        extractor = MockFrontmatterExtractor()

    return IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=extractor,
        evidence_root=evidence_root,
        failed_root=failed_root,
    )


@ingest_app.command("pubmed")
def ingest_pubmed(
    query: str = typer.Option(..., "--query", "-q", help="PubMed query"),
    since: int = typer.Option(None, "--since", help="Only papers since year YYYY"),
    limit: int = typer.Option(20, "--limit", help="Max records to fetch"),
    evidence_type: str = typer.Option("RCT", "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Search PubMed; for PMC OA hits, convert JATS -> draft markdown."""
    from hypertensiondb.ingest.jats_converter import jats_to_evidence
    from hypertensiondb.ingest.writer import write_evidence_md
    from hypertensiondb.utils import id_gen
    from hypertensiondb.utils.pinyin import to_first_author_pinyin

    if evidence_type not in {"RCT", "SR", "META", "GL", "TCM"}:
        typer.echo(f"Invalid type: {evidence_type}")
        raise typer.Exit(1)

    full_query = query
    if since:
        full_query = f"({query}) AND {since}:3000[pdat]"

    client = NCBIClient()
    pmids = client.esearch(query=full_query, db="pubmed", retmax=limit)
    if not pmids:
        typer.echo("No results.")
        return

    records = client.efetch_pubmed(pmids)
    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    # Ensure next_id writes its serials into the same evidence_root the CLI uses.
    id_gen.EVIDENCE_ROOT = ev_root

    ingested = 0
    skipped = 0
    for rec in records:
        if not rec.get("pmc_id"):
            typer.echo(f"  PMID {rec.get('pmid')}: no PMC OA - skipped")
            skipped += 1
            continue
        try:
            jats = client.efetch_pmc_xml(rec["pmc_id"])
            fm, sections = jats_to_evidence(jats, evidence_type=evidence_type)
            if rec.get("doi"):
                fm["doi"] = rec["doi"]
            if rec.get("pmid"):
                fm["pmid"] = rec["pmid"]
            if rec.get("journal"):
                fm["journal"] = rec["journal"]
            first_author = fm["authors"][0] if fm["authors"] else "Unknown"
            pinyin = to_first_author_pinyin(first_author)
            fm["id"] = id_gen.next_id(evidence_type, fm.get("year", 2026), pinyin)
            write_evidence_md(frontmatter=fm, sections=sections, evidence_root=ev_root)
            typer.echo(f"  PMID {rec['pmid']}: ingested as {fm['id']}")
            ingested += 1
        except Exception as e:
            typer.echo(f"  PMID {rec.get('pmid')}: FAILED - {e}")
            skipped += 1

    typer.echo(f"Done. {ingested} ingested, {skipped} skipped.")


@lint_app.command("run")
def lint_run() -> None:
    """Run corpus-wide validation: schema, filename, duplicates, draft pileup."""
    from hypertensiondb.quality.lint import run_lint

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    report = run_lint(ev_root)
    typer.echo(f"Total files: {report.total_files}")
    typer.echo(f"  draft={report.draft_count} reviewed={report.reviewed_count} "
               f"published={report.published_count}")
    if report.issues:
        typer.echo(f"\n{len(report.issues)} issues:")
        for issue in report.issues:
            typer.echo(f"  [{issue.code}] {issue.path}: {issue.detail}")
        raise typer.Exit(1)
    typer.echo("OK: no issues.")


def _build_pipeline():
    """Build IndexPipeline from environment variables."""
    from qdrant_client import QdrantClient
    from hypertensiondb.index.embedder_mock import MockEmbedder
    from hypertensiondb.index.sparse import SparseVectorizer
    from hypertensiondb.index.qdrant_index_client import QdrantIndexClient
    from hypertensiondb.index.pipeline import IndexPipeline

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant = QdrantClient(host=host, port=port)

    embedder_name = os.getenv("EMBEDDER", "mock")
    if embedder_name == "openai":
        from hypertensiondb.index.embedder_openai import OpenAIEmbedder
        embedder = OpenAIEmbedder(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"),
            dim=int(os.getenv("EMBED_DIM", "3072")),
        )
    elif embedder_name == "zhipu":
        from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
        embedder = ZhipuEmbedder(
            api_key=os.environ["ZHIPU_API_KEY"],
            dim=int(os.getenv("EMBED_DIM", "2048")),
        )
    else:
        embedder = MockEmbedder(dim=int(os.getenv("EMBED_DIM", "8")))

    idx_client = QdrantIndexClient(qdrant=qdrant, collection_name=COLLECTION_NAME)
    return IndexPipeline(
        embedder=embedder,
        sparse_vectorizer=SparseVectorizer(),
        qdrant_client=idx_client,
        collection_name=COLLECTION_NAME,
    )


@index_app.command("update")
def index_update() -> None:
    """Incrementally index new or modified reviewed/published evidence files."""
    from hypertensiondb.index.incremental import find_files_needing_reindex

    pipeline = _build_pipeline()
    files = find_files_needing_reindex(EVIDENCE_ROOT, pipeline._qdrant)
    if not files:
        typer.echo("Nothing to update — all files are up to date.")
        return
    typer.echo(f"Indexing {len(files)} file(s)…")
    total = 0
    for path in files:
        count = pipeline.index_file(path)
        typer.echo(f"  {path.name}: {count} chunk(s)")
        total += count
    typer.echo(f"Done. {total} chunk(s) indexed.")


@index_app.command("rebuild")
def index_rebuild(
    confirm: bool = typer.Option(False, "--confirm", help="Required to proceed with rebuild"),
) -> None:
    """Delete and rebuild the entire Qdrant collection from scratch."""
    if not confirm:
        typer.echo("This will DELETE and rebuild the entire collection.")
        typer.echo("Add --confirm to proceed.")
        raise typer.Exit(1)
    pipeline = _build_pipeline()
    typer.echo("Rebuilding collection…")
    total = pipeline.rebuild(EVIDENCE_ROOT)
    typer.echo(f"Done. {total} chunk(s) indexed.")


serve_app = typer.Typer(help="Run API server")
app.add_typer(serve_app, name="serve")


@serve_app.command("run")
def serve_run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start the FastAPI server using settings from environment variables."""
    import uvicorn
    from qdrant_client import QdrantClient

    from hypertensiondb.api.server import create_app
    from hypertensiondb.index.sparse import SparseVectorizer
    from hypertensiondb.retrieval.hybrid import HybridSearcher
    from hypertensiondb.retrieval.reranker_mock import MockReranker
    from hypertensiondb.retrieval.search import SearchEngine

    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)

    embedder_name = os.getenv("EMBEDDER", "mock")
    if embedder_name == "openai":
        from hypertensiondb.index.embedder_openai import OpenAIEmbedder
        embedder = OpenAIEmbedder(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"),
            dim=int(os.getenv("EMBED_DIM", "3072")),
        )
    elif embedder_name == "zhipu":
        from hypertensiondb.index.embedder_zhipu import ZhipuEmbedder
        embedder = ZhipuEmbedder(
            api_key=os.environ["ZHIPU_API_KEY"],
            dim=int(os.getenv("EMBED_DIM", "2048")),
        )
    else:
        from hypertensiondb.index.embedder_mock import MockEmbedder
        embedder = MockEmbedder(dim=int(os.getenv("EMBED_DIM", "8")))

    reranker_name = os.getenv("RERANKER", "mock")
    if reranker_name == "bge":
        from hypertensiondb.retrieval.reranker_bge import BGEReranker
        reranker = BGEReranker()
    elif reranker_name == "api":
        from hypertensiondb.retrieval.reranker_api import APIReranker
        reranker = APIReranker(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.huatuogpt.cn/v1"),
            model=os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
        )
    else:
        reranker = MockReranker()

    hybrid = HybridSearcher(qdrant=qdrant, collection_name=COLLECTION_NAME)
    engine = SearchEngine(
        embedder=embedder,
        sparse_vectorizer=SparseVectorizer(),
        hybrid_searcher=hybrid,
        reranker=reranker,
    )
    app = create_app(
        engine=engine, qdrant=qdrant, collection_name=COLLECTION_NAME,
        embedder_name=embedder.model_name, reranker_name=reranker.model_name,
    )
    uvicorn.run(app, host=host, port=port, reload=reload)


@app.command("publish")
def publish_cmd(
    evidence_id: str = typer.Argument(..., help="Evidence ID like EV-RCT-2026-X-001"),
    to: str = typer.Option("reviewed", "--to", help="reviewed|published"),
) -> None:
    """Promote a draft/reviewed file to the next status (with safety checks)."""
    from hypertensiondb.quality.publish import publish_evidence, PublishError

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    try:
        path = publish_evidence(evidence_id, evidence_root=ev_root, target_status=to)
        typer.echo(f"OK: {evidence_id} -> {to}")
        typer.echo(f"  {path}")
    except PublishError as e:
        typer.echo(f"FAILED: {e}")
        raise typer.Exit(2)


@app.command("stats")
def stats_cmd() -> None:
    """Print corpus health summary."""
    from hypertensiondb.quality.stats import compute_stats

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    s = compute_stats(ev_root)
    typer.echo(f"Total: {s.total}")
    typer.echo(f"  by type:   {s.by_type}")
    typer.echo(f"  by status: {s.by_status}")
    typer.echo(f"  by grade:  {s.by_grade}")
    typer.echo(f"  by year:   {s.by_year}")
    typer.echo(f"  by language: {s.by_language}")
    if s.draft_pileup_alert:
        typer.echo("\nWARNING: DRAFT PILE-UP: more than 20% of files are draft. Run 'hdb lint' "
                   "and review them.")
