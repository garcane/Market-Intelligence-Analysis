"""Local-only pipeline runner. Jobs come from a fixed whitelist of
`python -m` modules; the only argument a caller may set is the news
backfill's request cap. One job runs at a time, as a subprocess, with its
output written to a log file that the UI polls.

This router is only registered in local mode, and every endpoint also
requires the caller to be on localhost (api.deps.require_local).
"""
from __future__ import annotations

import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api import data
from api.deps import require_local
from src.config import CACHE_DIR, ROOT_DIR

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"], dependencies=[Depends(require_local)])

LOG_DIR = CACHE_DIR / "pipeline_logs"
TAIL_LINES = 80

JOBS: dict[str, dict] = {
    "ingest": {"module": "src.ingestion.run_ingestion", "label": "Ingest prices and news",
               "description": "Refresh prices for the full universe, plus current news (Google News, Yahoo Finance)."},
    "news_backfill": {"module": "src.ingestion.run_news_backfill", "label": "News backfill",
                      "description": "Backfill older news (Finnhub, Alpha Vantage) within today's quotas and collect the latest Yahoo Finance ticker news. Run daily."},
    "sentiment": {"module": "src.sentiment.run_sentiment", "label": "Score sentiment",
                  "description": "Score every article with VADER and TextBlob."},
    "features": {"module": "src.features.run_features", "label": "Build features",
                 "description": "Rebuild the feature table from prices and sentiment."},
    "target": {"module": "src.features.run_target", "label": "Build targets",
               "description": "Rebuild forward-return targets."},
    "split": {"module": "src.models.run_split", "label": "Temporal split",
              "description": "Rebuild the train / validation / test split."},
    "train": {"module": "src.models.train_baselines", "label": "Train models",
              "description": "Retrain the baselines and write the model report (validation only)."},
    "explain": {"module": "src.models.run_explain", "label": "Explainability",
                "description": "Recompute importance, SHAP and permutation importance."},
    "indices": {"module": "src.analytics.run_indices", "label": "AI indices",
                "description": "Rebuild the thematic AI indices report."},
    "event_study": {"module": "src.analytics.run_event_study", "label": "Event study",
                    "description": "Recompute abnormal returns around AI events."},
}


@dataclass
class Job:
    id: str
    name: str
    command: list[str]
    log_path: Path
    started_at: str
    status: str = "running"
    returncode: int | None = None
    finished_at: str | None = None
    process: subprocess.Popen | None = field(default=None, repr=False)

    def as_dict(self, tail: bool = True) -> dict:
        out = {"id": self.id, "name": self.name, "status": self.status, "returncode": self.returncode,
               "started_at": self.started_at, "finished_at": self.finished_at,
               "command": " ".join(["python", *self.command[1:]])}
        if tail:
            out["log_tail"] = _tail(self.log_path)
        return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tail(path: Path, n: int = TAIL_LINES) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


class JobRunner:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def current(self) -> Job | None:
        return next((j for j in self.jobs.values() if j.status == "running"), None)

    def start(self, name: str, args: list[str]) -> Job:
        with self.lock:
            running = self.current()
            if running:
                raise HTTPException(409, f"job {running.name!r} is still running")
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            job_id = uuid.uuid4().hex[:12]
            command = [sys.executable, "-m", JOBS[name]["module"], *args]
            job = Job(id=job_id, name=name, command=command, log_path=LOG_DIR / f"{job_id}.log",
                      started_at=_now())
            log = open(job.log_path, "w", encoding="utf-8")
            job.process = subprocess.Popen(command, cwd=ROOT_DIR, stdout=log, stderr=subprocess.STDOUT)
            self.jobs[job_id] = job
        threading.Thread(target=self._wait, args=(job, log), daemon=True).start()
        return job

    def _wait(self, job: Job, log) -> None:
        job.returncode = job.process.wait()
        log.close()
        job.finished_at = _now()
        job.status = "succeeded" if job.returncode == 0 else "failed"
        data.clear_cache()


runner = JobRunner()


class RunRequest(BaseModel):
    max_requests: int | None = Field(None, ge=1, le=5000, description="news_backfill only: cap on network calls")


@router.get("/jobs")
def list_jobs() -> dict:
    history = sorted(runner.jobs.values(), key=lambda j: j.started_at, reverse=True)
    return {"available": [{"name": k, "label": v["label"], "description": v["description"]} for k, v in JOBS.items()],
            "running": runner.current().id if runner.current() else None,
            "history": [j.as_dict(tail=False) for j in history[:20]]}


@router.post("/run/{name}", status_code=202)
def run_job(name: str, body: RunRequest | None = None) -> dict:
    if name not in JOBS:
        raise HTTPException(404, f"unknown job {name!r}")
    args: list[str] = []
    if body and body.max_requests is not None:
        if name != "news_backfill":
            raise HTTPException(422, "max_requests only applies to news_backfill")
        args = ["--max-requests", str(body.max_requests)]
    return runner.start(name, args).as_dict()


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = runner.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job id")
    return job.as_dict()
