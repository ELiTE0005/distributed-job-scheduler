import argparse
from app.worker_service import WorkerService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Job Scheduler Worker")
    parser.add_argument("--concurrency", type=int, default=3,
                         help="Number of jobs this worker instance can run at once")
    args = parser.parse_args()

    worker = WorkerService(concurrency=args.concurrency)
    worker.start()