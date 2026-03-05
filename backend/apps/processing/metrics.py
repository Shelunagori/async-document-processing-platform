from prometheus_client import Counter, Histogram


documents_processed_total = Counter(
    "documents_processed_total",
    "Total number of processed documents grouped by result.",
    labelnames=("result",),
)

processing_time_seconds = Histogram(
    "processing_time_seconds",
    "Document processing pipeline execution time in seconds.",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
)

failed_jobs_total = Counter(
    "failed_jobs_total",
    "Total number of failed document processing jobs.",
)
