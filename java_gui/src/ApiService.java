import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * HTTP client that communicates with the Python BitTorrent REST API.
 *
 * Provides methods to start downloads, get status, and control
 * (pause/resume/cancel) torrent downloads.
 */
public class ApiService {

    private final String baseUrl;
    private final HttpClient httpClient;

    /**
     * Status information for a single torrent download.
     */
    public static class TorrentStatus {
        public String id;
        public String name;
        public long size;
        public double progress;
        public double downloadSpeed;
        public double uploadSpeed;
        public int connectedPeers;
        public String state;
        public long downloaded;
        public long uploaded;
        public double elapsedTime;
        public String pieceAlgorithm;
        public String peerAlgorithm;
        public String downloadPath;

        public static TorrentStatus fromJson(JSONObject json) {
            TorrentStatus status = new TorrentStatus();
            status.id = json.optString("id", "");
            status.name = json.optString("name", "");
            status.size = json.optLong("size", 0);
            status.progress = json.optDouble("progress", 0.0);
            status.downloadSpeed = json.optDouble("download_speed", 0.0);
            status.uploadSpeed = json.optDouble("upload_speed", 0.0);
            status.connectedPeers = json.optInt("connected_peers", 0);
            status.state = json.optString("state", "Unknown");
            status.downloaded = json.optLong("downloaded", 0);
            status.uploaded = json.optLong("uploaded", 0);
            status.elapsedTime = json.optDouble("elapsed_time", 0.0);
            status.pieceAlgorithm = json.optString("piece_algorithm", "");
            status.peerAlgorithm = json.optString("peer_algorithm", "");
            status.downloadPath = json.optString("download_path", "");
            return status;
        }

        @Override
        public String toString() {
            return String.format("%s [%s] %.1f%% - %.1f KB/s - %d peers",
                    name, state, progress, downloadSpeed / 1024, connectedPeers);
        }
    }

    /**
     * Create an ApiService connecting to the given base URL.
     *
     * @param baseUrl Base URL of the Python API (e.g., "http://localhost:5000")
     */
    public ApiService(String baseUrl) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    /**
     * Default constructor connecting to localhost:5000.
     */
    public ApiService() {
        this("http://localhost:5000");
    }

    /**
     * Start a new download from a .torrent file.
     *
     * @param torrentFile The .torrent file to upload.
     * @return The torrent ID assigned by the server.
     * @throws IOException      If there is a network or file error.
     * @throws ApiException     If the server returns an error.
     */
    public String startDownload(File torrentFile) throws IOException, ApiException {
        return startDownload(torrentFile, "rarest_first", "tit_for_tat", null);
    }

    /**
     * Start a new download with specific algorithms and download directory.
     *
     * @param torrentFile    The .torrent file.
     * @param pieceAlgorithm Piece selection algorithm ("rarest_first" or "random").
     * @param peerAlgorithm  Peer selection algorithm ("tit_for_tat" or "round_robin").
     * @param downloadDir    Directory to save the downloaded file (null for server default).
     * @return The torrent ID.
     * @throws IOException  If there is a network or file error.
     * @throws ApiException If the server returns an error.
     */
    public String startDownload(File torrentFile, String pieceAlgorithm, String peerAlgorithm,
                                String downloadDir)
            throws IOException, ApiException {
        // Build multipart request
        String boundary = "----FormBoundary" + System.currentTimeMillis();
        byte[] fileBytes = Files.readAllBytes(torrentFile.toPath());

        StringBuilder bodyBuilder = new StringBuilder();
        // Torrent file part
        bodyBuilder.append("--").append(boundary).append("\r\n");
        bodyBuilder.append("Content-Disposition: form-data; name=\"torrent_file\"; filename=\"")
                .append(torrentFile.getName()).append("\"\r\n");
        bodyBuilder.append("Content-Type: application/x-bittorrent\r\n\r\n");

        byte[] headerBytes = bodyBuilder.toString().getBytes();

        String algorithmPart = "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"piece_algorithm\"\r\n\r\n" +
                pieceAlgorithm +
                "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"peer_algorithm\"\r\n\r\n" +
                peerAlgorithm;

        // Add download directory if specified
        if (downloadDir != null && !downloadDir.isEmpty()) {
            algorithmPart += "\r\n--" + boundary + "\r\n" +
                    "Content-Disposition: form-data; name=\"download_dir\"\r\n\r\n" +
                    downloadDir;
        }

        algorithmPart += "\r\n--" + boundary + "--\r\n";

        byte[] footerBytes = algorithmPart.getBytes();

        // Combine
        byte[] body = new byte[headerBytes.length + fileBytes.length + footerBytes.length];
        System.arraycopy(headerBytes, 0, body, 0, headerBytes.length);
        System.arraycopy(fileBytes, 0, body, headerBytes.length, fileBytes.length);
        System.arraycopy(footerBytes, 0, body, headerBytes.length + fileBytes.length, footerBytes.length);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents"))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                .build();

        HttpResponse<String> response = sendRequest(request);

        if (response.statusCode() != 201) {
            throw new ApiException("Failed to start download: " + response.body());
        }

        JSONObject json = new JSONObject(response.body());
        return json.getString("id");
    }

    /**
     * Get status of all active downloads.
     *
     * @return List of TorrentStatus objects.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public List<TorrentStatus> getStatus() throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents"))
                .GET()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);

        JSONArray jsonArray = new JSONArray(response.body());
        List<TorrentStatus> statuses = new ArrayList<>();
        for (int i = 0; i < jsonArray.length(); i++) {
            statuses.add(TorrentStatus.fromJson(jsonArray.getJSONObject(i)));
        }
        return statuses;
    }

    /**
     * Get status of a specific download.
     *
     * @param torrentId The torrent ID.
     * @return TorrentStatus for the specified torrent.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public TorrentStatus getStatus(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId))
                .GET()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);

        return TorrentStatus.fromJson(new JSONObject(response.body()));
    }

    /**
     * Pause a specific download.
     *
     * @param torrentId The torrent ID to pause.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public void pause(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId + "/pause"))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
    }

    /**
     * Resume a paused download.
     *
     * @param torrentId The torrent ID to resume.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public void resume(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId + "/resume"))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
    }

    /**
     * Cancel a specific download.
     *
     * @param torrentId The torrent ID to cancel.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public void cancel(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId + "/cancel"))
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
    }

    /**
     * Remove a download from the list.
     *
     * Stops it if still active and deletes its server-side state, but keeps
     * the downloaded file on disk. After this the torrent no longer appears
     * in the status list.
     *
     * @param torrentId The torrent ID to remove.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public void delete(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId))
                .DELETE()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
    }

    /**
     * Get download history from the server.
     *
     * @return JSON string of download history.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public String getHistory() throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/history"))
                .GET()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
        return response.body();
    }

    /**
     * Clear all download history from the server database.
     *
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public void clearHistory() throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/history"))
                .DELETE()
                .build();
        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
    }

    /**
     * Get per-piece algorithm statistics for a specific torrent.
     *
     * @param torrentId The torrent ID.
     * @return JSONArray of algorithm stat rows.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public JSONArray getAlgorithmStats(String torrentId) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/algorithm-stats/" + torrentId))
                .GET()
                .build();
        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
        return new JSONArray(response.body());
    }

    /**
     * Get aggregated stats summary for all torrents (for comparison table).
     *
     * @return JSONArray of summary rows.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public JSONArray getStatsSummary() throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/stats-summary"))
                .GET()
                .build();
        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
        return new JSONArray(response.body());
    }

    /**
     * Get event log from the server.
     *
     * @param limit Maximum number of events to retrieve.
     * @return JSON string of events.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public String getEvents(int limit) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/events?limit=" + limit))
                .GET()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);
        return response.body();
    }

    /**
     * Get live log messages from a running download.
     *
     * @param torrentId The torrent ID.
     * @param sinceSeq  Only return logs with seq greater than this.
     * @return JSONArray of log entries.
     * @throws IOException  If there is a network error.
     * @throws ApiException If the server returns an error.
     */
    public JSONArray getLogs(String torrentId, int sinceSeq) throws IOException, ApiException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/torrents/" + torrentId + "/logs?since=" + sinceSeq))
                .GET()
                .build();

        HttpResponse<String> response = sendRequest(request);
        checkResponse(response, 200);

        JSONObject json = new JSONObject(response.body());
        return json.getJSONArray("logs");
    }

    /**
     * Check if the API server is reachable.
     *
     * @return true if the server responds to health check.
     */
    public boolean isServerAvailable() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/health"))
                    .timeout(Duration.ofSeconds(5))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }

    // -- Helper methods --

    private HttpResponse<String> sendRequest(HttpRequest request) throws IOException, ApiException {
        try {
            return httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ApiException("Request interrupted: " + e.getMessage());
        }
    }

    private void checkResponse(HttpResponse<String> response, int expectedStatus) throws ApiException {
        if (response.statusCode() != expectedStatus) {
            String errorMsg;
            try {
                JSONObject json = new JSONObject(response.body());
                errorMsg = json.optString("error", response.body());
            } catch (Exception e) {
                errorMsg = response.body();
            }
            throw new ApiException("API error (HTTP " + response.statusCode() + "): " + errorMsg);
        }
    }

    /**
     * Exception for API communication errors.
     */
    public static class ApiException extends Exception {
        public ApiException(String message) {
            super(message);
        }

        public ApiException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
