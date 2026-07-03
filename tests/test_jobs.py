def _setup_project_and_queue(client, headers):
    project = client.post("/projects", json={"name": "Test Project"}, headers=headers).json()
    queue = client.post(
        f"/projects/{project['id']}/queues",
        json={"name": "test-queue", "max_concurrency": 5},
        headers=headers,
    ).json()
    return project["id"], queue["id"]


def test_create_immediate_job(client, auth_headers):
    project_id, queue_id = _setup_project_and_queue(client, auth_headers)
    res = client.post(
        f"/projects/{project_id}/queues/{queue_id}/jobs",
        json={"job_type": "immediate", "payload": {"task": "x"}, "priority": 0},
        headers=auth_headers,
    )
    assert res.status_code == 201
    jobs = res.json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "pending"


def test_delayed_job_requires_delay_seconds(client, auth_headers):
    project_id, queue_id = _setup_project_and_queue(client, auth_headers)
    res = client.post(
        f"/projects/{project_id}/queues/{queue_id}/jobs",
        json={"job_type": "delayed", "payload": {}},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_batch_job_creates_multiple_rows(client, auth_headers):
    project_id, queue_id = _setup_project_and_queue(client, auth_headers)
    res = client.post(
        f"/projects/{project_id}/queues/{queue_id}/jobs",
        json={"job_type": "batch", "payload": {}, "batch_size": 5},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert len(res.json()) == 5


def test_paused_queue_rejects_new_jobs(client, auth_headers):
    project_id, queue_id = _setup_project_and_queue(client, auth_headers)
    client.patch(
        f"/projects/{project_id}/queues/{queue_id}",
        json={"is_paused": True},
        headers=auth_headers,
    )
    res = client.post(
        f"/projects/{project_id}/queues/{queue_id}/jobs",
        json={"job_type": "immediate", "payload": {}},
        headers=auth_headers,
    )
    assert res.status_code == 400