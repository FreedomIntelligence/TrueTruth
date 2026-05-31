#!/usr/bin/env python3
"""Interactive scaffold for new evidence entries."""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from hypertensiondb.schema.base import EvidenceType
from hypertensiondb.utils.pinyin import to_first_author_pinyin
from hypertensiondb.utils.id_gen import next_id

_TYPE_DIR = {
    EvidenceType.RCT: "rcts",
    EvidenceType.SR: "systematic_reviews",
    EvidenceType.META: "meta_analyses",
    EvidenceType.GL: "guidelines",
    EvidenceType.TCM: "tcm",
}

TEMPLATE = """\
---
id: {ev_id}
type: {ev_type}
title:
  zh:
  en:
authors: []
year: {year}
language: zh
doi:
pmid:
full_text_status: complete
source: manual_pdf
ingested_at: {today}
status: draft
pico:
  population:
    condition:
    sample_size:
  intervention:
    name:
    drug_class: []
  comparison:
    name:
  outcomes:
    primary: []
    secondary: []
risk_of_bias:
  tool: RoB2
  overall:
  domains: {{}}
grade:
  level:
  reasons: []
tags: []
---

## 临床要点 / Clinical Bottom Line

（在此填写 1-3 句关键结论）

## 中文摘要

## English Abstract

## 背景 / Background

## 方法 / Methods

## 结果 / Results

## 讨论 / Discussion

## 结论 / Conclusion

## 参考文献 / References
"""

app = typer.Typer()


@app.command()
def main(
    ev_type: str = typer.Option(..., prompt="Evidence type (RCT/SR/META/GL/TCM)"),
    year: int = typer.Option(..., prompt="Publication year"),
    first_author: str = typer.Option(..., prompt="First author (Chinese name or English surname)"),
) -> None:
    ev_type_upper = ev_type.strip().upper()
    try:
        et = EvidenceType(ev_type_upper)
    except ValueError:
        typer.echo(f"Unknown type: {ev_type_upper}. Must be one of {list(EvidenceType)}")
        raise typer.Exit(1)

    pinyin = to_first_author_pinyin(first_author.strip())
    ev_id = next_id(ev_type_upper, year, pinyin)
    ev_dir = Path("evidence") / _TYPE_DIR[et]
    ev_dir.mkdir(parents=True, exist_ok=True)
    out_path = ev_dir / f"{ev_id}.md"

    content = TEMPLATE.format(
        ev_id=ev_id,
        ev_type=ev_type_upper,
        year=year,
        today=date.today().isoformat(),
    )
    out_path.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {out_path}")
    typer.echo(f"ID: {ev_id}")


if __name__ == "__main__":
    app()
