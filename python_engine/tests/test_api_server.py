"""
Tests for the API server module.
"""

import json
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from python_engine.api_server import app, init_database, DB_PATH


@pytest.fixture
def client(tmp_path):
    """Create a test client with temporary database."""
    # Use temp paths
    test_db = str(tmp_path / "test_history.db")
    test_state = str(tmp_path / "state")
    test_downloads = str(tmp_path / "downloads")

    os.makedirs(test_state, exist_ok=True)
    os.makedirs(test_downloads, exist_ok=True)

    with patch('python_engine.api_server.DB_PATH', test_db), \
         patch('python_engine.api_server.STATE_DIR', test_state), \
         patch('python_engine.api_server.DOWNLOAD_DIR', test_downloads):

        init_database()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client


class TestHealthCheck:
    def test_health(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'timestamp' in data


class TestGetTorrents:
    def test_get_all_empty(self, client):
        response = client.get('/torrents')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_get_nonexistent_torrent(self, client):
        response = client.get('/torrents/nonexistent')
        assert response.status_code == 404


class TestTorrentOperations:
    def test_start_no_file(self, client):
        response = client.post('/torrents')
        assert response.status_code == 400

    def test_pause_nonexistent(self, client):
        response = client.post('/torrents/nonexistent/pause')
        assert response.status_code == 404

    def test_resume_nonexistent(self, client):
        response = client.post('/torrents/nonexistent/resume')
        assert response.status_code == 404

    def test_cancel_nonexistent(self, client):
        response = client.post('/torrents/nonexistent/cancel')
        assert response.status_code == 404


class TestHistoryEndpoints:
    def test_get_history(self, client):
        response = client.get('/history')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_events(self, client):
        response = client.get('/events')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_get_events_with_limit(self, client):
        response = client.get('/events?limit=10')
        assert response.status_code == 200

    def test_get_events_with_torrent_id(self, client):
        response = client.get('/events?torrent_id=test123')
        assert response.status_code == 200

    def test_get_algorithm_stats(self, client):
        response = client.get('/algorithm-stats/test123')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestDatabase:
    def test_init_creates_tables(self, tmp_path):
        test_db = str(tmp_path / "test.db")
        with patch('python_engine.api_server.DB_PATH', test_db):
            init_database()

        import sqlite3
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert 'torrents' in tables
        assert 'performance_stats' in tables
        assert 'algorithm_stats' in tables
        assert 'events' in tables
