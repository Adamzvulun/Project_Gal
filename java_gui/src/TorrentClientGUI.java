import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Main GUI window for the BitTorrent client.
 *
 * Displays active downloads with progress, speed, and peer information.
 * Provides controls for adding, pausing, resuming, and cancelling downloads.
 * Communicates with the Python BitTorrent engine via the REST API.
 */
public class TorrentClientGUI extends JFrame {

    // Table columns
    private static final String[] COLUMN_NAMES = {
            "Name", "Size", "Progress", "Speed", "Peers", "State", "Location", "ID"
    };
    private static final int COL_NAME = 0;
    private static final int COL_SIZE = 1;
    private static final int COL_PROGRESS = 2;
    private static final int COL_SPEED = 3;
    private static final int COL_PEERS = 4;
    private static final int COL_STATE = 5;
    private static final int COL_LOCATION = 6;
    private static final int COL_ID = 7;

    private final ApiService apiService;
    private final DefaultTableModel tableModel;
    private final JTable downloadTable;
    private final JTextArea logArea;
    private final JLabel statusLabel;
    private final ScheduledExecutorService scheduler;

    // Control buttons
    private JButton pauseButton;
    private JButton resumeButton;
    private JButton cancelButton;

    // Algorithm selection combos
    private JComboBox<String> pieceAlgorithmCombo;
    private JComboBox<String> peerAlgorithmCombo;

    // Track last log sequence per torrent for incremental polling
    private final Map<String, Integer> logSeqTracker = new HashMap<>();

    // Track previous download states to detect completion transitions
    private final Map<String, String> previousStates = new HashMap<>();

    /**
     * Create the main application window.
     */
    public TorrentClientGUI() {
        super("מערכת שיתוף קבצים מבוזרת בסגנון BitTorrent");

        this.apiService = new ApiService();
        this.scheduler = Executors.newSingleThreadScheduledExecutor();

        // Window setup
        setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
        addWindowListener(new WindowAdapter() {
            @Override
            public void windowClosing(WindowEvent e) {
                shutdown();
            }
        });
        setSize(900, 600);
        setMinimumSize(new Dimension(700, 400));
        setLocationRelativeTo(null);

        // Downloads table (must be created before toolbar, which references it)
        tableModel = new DefaultTableModel(COLUMN_NAMES, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }

            @Override
            public Class<?> getColumnClass(int columnIndex) {
                if (columnIndex == COL_PROGRESS) return Double.class;
                return String.class;
            }
        };
        downloadTable = new JTable(tableModel);
        configureTable();

        // Main layout
        JPanel mainPanel = new JPanel(new BorderLayout(5, 5));
        mainPanel.setBorder(new EmptyBorder(10, 10, 10, 10));

        // Toolbar
        mainPanel.add(createToolbar(), BorderLayout.NORTH);

        // Split pane: downloads table on top, logs on bottom
        JSplitPane splitPane = new JSplitPane(JSplitPane.VERTICAL_SPLIT);
        splitPane.setResizeWeight(0.7);

        splitPane.setTopComponent(new JScrollPane(downloadTable));

        // Log area
        logArea = new JTextArea();
        logArea.setEditable(false);
        logArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
        JPanel logPanel = new JPanel(new BorderLayout());
        logPanel.add(new JLabel("  Event Log:"), BorderLayout.NORTH);
        logPanel.add(new JScrollPane(logArea), BorderLayout.CENTER);
        splitPane.setBottomComponent(logPanel);

        mainPanel.add(splitPane, BorderLayout.CENTER);

        // Status bar
        statusLabel = new JLabel(" Ready");
        statusLabel.setBorder(BorderFactory.createLoweredBevelBorder());
        mainPanel.add(statusLabel, BorderLayout.SOUTH);

        setContentPane(mainPanel);

        // Start periodic status updates
        startStatusUpdater();

        log("Application started. Connecting to BitTorrent engine...");
        checkServerConnection();
    }

    /**
     * Create the toolbar with action buttons.
     */
    private JToolBar createToolbar() {
        JToolBar toolbar = new JToolBar();
        toolbar.setFloatable(false);

        // Add Torrent button
        JButton addButton = new JButton("Add Torrent");
        addButton.setToolTipText("Select a .torrent file to download");
        addButton.addActionListener(this::onAddTorrent);
        toolbar.add(addButton);

        toolbar.addSeparator();

        // Pause button
        pauseButton = new JButton("Pause");
        pauseButton.setToolTipText("Pause selected download");
        pauseButton.setEnabled(false);
        pauseButton.addActionListener(this::onPause);
        toolbar.add(pauseButton);

        // Resume button
        resumeButton = new JButton("Resume");
        resumeButton.setToolTipText("Resume selected download");
        resumeButton.setEnabled(false);
        resumeButton.addActionListener(this::onResume);
        toolbar.add(resumeButton);

        // Cancel button
        cancelButton = new JButton("Cancel");
        cancelButton.setToolTipText("Cancel selected download");
        cancelButton.setEnabled(false);
        cancelButton.addActionListener(this::onCancel);
        toolbar.add(cancelButton);

        toolbar.addSeparator();

        // History button
        JButton historyButton = new JButton("History");
        historyButton.setToolTipText("View download history");
        historyButton.addActionListener(this::onShowHistory);
        toolbar.add(historyButton);

        // Statistics button
        JButton statsButton = new JButton("סטטיסטיקות");
        statsButton.setToolTipText("Algorithm statistics visualization");
        statsButton.addActionListener(this::onShowStats);
        toolbar.add(statsButton);

        // Algorithm selection
        toolbar.addSeparator();
        toolbar.add(new JLabel(" Piece: "));
        pieceAlgorithmCombo = new JComboBox<>(
                new String[]{"Rarest First", "Random"});
        pieceAlgorithmCombo.setMaximumSize(new Dimension(120, 30));
        toolbar.add(pieceAlgorithmCombo);

        toolbar.add(new JLabel(" Peer: "));
        peerAlgorithmCombo = new JComboBox<>(
                new String[]{"Tit-for-Tat", "Round Robin"});
        peerAlgorithmCombo.setMaximumSize(new Dimension(120, 30));
        toolbar.add(peerAlgorithmCombo);

        // Enable/disable buttons based on selection
        downloadTable.getSelectionModel().addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                updateButtonStates();
            }
        });

        return toolbar;
    }

    /**
     * Configure the downloads table appearance.
     */
    private void configureTable() {
        downloadTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        downloadTable.setRowHeight(25);
        downloadTable.getTableHeader().setReorderingAllowed(false);

        // Column widths
        downloadTable.getColumnModel().getColumn(COL_NAME).setPreferredWidth(200);
        downloadTable.getColumnModel().getColumn(COL_SIZE).setPreferredWidth(80);
        downloadTable.getColumnModel().getColumn(COL_PROGRESS).setPreferredWidth(120);
        downloadTable.getColumnModel().getColumn(COL_SPEED).setPreferredWidth(100);
        downloadTable.getColumnModel().getColumn(COL_PEERS).setPreferredWidth(60);
        downloadTable.getColumnModel().getColumn(COL_STATE).setPreferredWidth(80);
        downloadTable.getColumnModel().getColumn(COL_LOCATION).setPreferredWidth(200);
        downloadTable.getColumnModel().getColumn(COL_ID).setPreferredWidth(70);

        // Progress bar renderer
        downloadTable.getColumnModel().getColumn(COL_PROGRESS).setCellRenderer(
                new ProgressBarRenderer());
    }

    // -- Action Handlers --

    private void onAddTorrent(ActionEvent e) {
        // Step 1: Choose .torrent file
        JFileChooser torrentChooser = new JFileChooser();
        torrentChooser.setFileFilter(new javax.swing.filechooser.FileNameExtensionFilter(
                "Torrent Files (*.torrent)", "torrent"));
        torrentChooser.setDialogTitle("Select Torrent File");

        if (torrentChooser.showOpenDialog(this) != JFileChooser.APPROVE_OPTION) {
            return;
        }
        File torrentFile = torrentChooser.getSelectedFile();

        // Step 2: Choose save directory
        JFileChooser dirChooser = new JFileChooser();
        dirChooser.setDialogTitle("Choose Download Location");
        dirChooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
        dirChooser.setAcceptAllFileFilterUsed(false);

        if (dirChooser.showOpenDialog(this) != JFileChooser.APPROVE_OPTION) {
            return;
        }
        File downloadDir = dirChooser.getSelectedFile();

        addTorrent(torrentFile, downloadDir.getAbsolutePath());
    }

    private void addTorrent(File torrentFile, String downloadDir) {
        setStatus("Starting download: " + torrentFile.getName());
        new Thread(() -> {
            try {
                // Get selected algorithms from toolbar combos
                String pieceAlgo = pieceAlgorithmCombo.getSelectedItem().toString()
                        .toLowerCase().replace(" ", "_").replace("-", "_");
                String peerAlgo = peerAlgorithmCombo.getSelectedItem().toString()
                        .toLowerCase().replace(" ", "_").replace("-", "_");

                String id = apiService.startDownload(torrentFile, pieceAlgo, peerAlgo, downloadDir);
                log("Download started: " + torrentFile.getName() + " → " + downloadDir + " (ID: " + id + ")");
                SwingUtilities.invokeLater(this::refreshStatus);
            } catch (Exception ex) {
                log("ERROR: Failed to start download: " + ex.getMessage());
                SwingUtilities.invokeLater(() ->
                        JOptionPane.showMessageDialog(this,
                                "Failed to start download:\n" + ex.getMessage(),
                                "Error", JOptionPane.ERROR_MESSAGE));
            }
        }).start();
    }

    private void onPause(ActionEvent e) {
        String id = getSelectedTorrentId();
        if (id == null) return;

        new Thread(() -> {
            try {
                apiService.pause(id);
                log("Paused download: " + id);
                SwingUtilities.invokeLater(this::refreshStatus);
            } catch (Exception ex) {
                log("ERROR: Failed to pause: " + ex.getMessage());
            }
        }).start();
    }

    private void onResume(ActionEvent e) {
        String id = getSelectedTorrentId();
        if (id == null) return;

        new Thread(() -> {
            try {
                apiService.resume(id);
                log("Resumed download: " + id);
                SwingUtilities.invokeLater(this::refreshStatus);
            } catch (Exception ex) {
                log("ERROR: Failed to resume: " + ex.getMessage());
            }
        }).start();
    }

    private void onCancel(ActionEvent e) {
        String id = getSelectedTorrentId();
        if (id == null) return;

        int confirm = JOptionPane.showConfirmDialog(this,
                "Are you sure you want to cancel this download?",
                "Confirm Cancel", JOptionPane.YES_NO_OPTION);
        if (confirm != JOptionPane.YES_OPTION) return;

        new Thread(() -> {
            try {
                apiService.cancel(id);
                log("Cancelled download: " + id);
                SwingUtilities.invokeLater(this::refreshStatus);
            } catch (Exception ex) {
                log("ERROR: Failed to cancel: " + ex.getMessage());
            }
        }).start();
    }

    private void onShowHistory(ActionEvent e) {
        new Thread(() -> {
            try {
                String history = apiService.getHistory();
                SwingUtilities.invokeLater(() -> {
                    JTextArea textArea = new JTextArea(history);
                    textArea.setEditable(false);
                    textArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
                    JScrollPane scrollPane = new JScrollPane(textArea);
                    scrollPane.setPreferredSize(new Dimension(600, 400));
                    JOptionPane.showMessageDialog(this, scrollPane,
                            "Download History", JOptionPane.INFORMATION_MESSAGE);
                });
            } catch (Exception ex) {
                log("ERROR: Failed to load history: " + ex.getMessage());
            }
        }).start();
    }

    private void onShowStats(ActionEvent e) {
        AlgorithmStatsDialog dialog = new AlgorithmStatsDialog(this, apiService);
        dialog.setVisible(true);
    }

    // -- Status Update --

    private void startStatusUpdater() {
        scheduler.scheduleAtFixedRate(() -> {
            try {
                SwingUtilities.invokeLater(this::refreshStatus);
            } catch (Exception e) {
                // Ignore refresh errors
            }
        }, 1, 2, TimeUnit.SECONDS);
    }

    private void refreshStatus() {
        new Thread(() -> {
            try {
                List<ApiService.TorrentStatus> statuses = apiService.getStatus();
                SwingUtilities.invokeLater(() -> updateTable(statuses));

                // Poll logs for each active download
                for (ApiService.TorrentStatus status : statuses) {
                    if ("Running".equals(status.state) || "Error".equals(status.state) || "Completed".equals(status.state)) {
                        int since = logSeqTracker.getOrDefault(status.id, 0);
                        try {
                            JSONArray logs = apiService.getLogs(status.id, since);
                            if (logs.length() > 0) {
                                int maxSeq = since;
                                for (int i = 0; i < logs.length(); i++) {
                                    JSONObject entry = logs.getJSONObject(i);
                                    int seq = entry.getInt("seq");
                                    String msg = entry.getString("msg");
                                    if (seq > maxSeq) maxSeq = seq;
                                    SwingUtilities.invokeLater(() -> log("[engine] " + msg));
                                }
                                logSeqTracker.put(status.id, maxSeq);
                            }
                        } catch (Exception ex) {
                            // Ignore log polling errors
                        }
                    }
                }
            } catch (Exception e) {
                // Server might not be running yet
            }
        }).start();
    }

    private void updateTable(List<ApiService.TorrentStatus> statuses) {
        // Remember selection
        int selectedRow = downloadTable.getSelectedRow();
        String selectedId = getSelectedTorrentId();

        // Detect completion transitions and show notification
        for (ApiService.TorrentStatus status : statuses) {
            String prevState = previousStates.get(status.id);
            if ("Completed".equals(status.state) && !"Completed".equals(prevState)) {
                String msg = status.name + "\nSaved to: " + status.downloadPath;
                SwingUtilities.invokeLater(() ->
                    JOptionPane.showMessageDialog(this, msg, "Download Complete",
                            JOptionPane.INFORMATION_MESSAGE)
                );
            }
            previousStates.put(status.id, status.state);
        }

        tableModel.setRowCount(0);
        for (ApiService.TorrentStatus status : statuses) {
            tableModel.addRow(new Object[]{
                    status.name,
                    formatSize(status.size),
                    status.progress,
                    formatSpeed(status.downloadSpeed),
                    String.valueOf(status.connectedPeers),
                    status.state,
                    status.downloadPath,
                    status.id
            });
        }

        // Restore selection
        if (selectedId != null) {
            for (int i = 0; i < tableModel.getRowCount(); i++) {
                if (selectedId.equals(tableModel.getValueAt(i, COL_ID))) {
                    downloadTable.setRowSelectionInterval(i, i);
                    break;
                }
            }
        }

        // Update status bar
        int active = (int) statuses.stream()
                .filter(s -> "Running".equals(s.state))
                .count();
        setStatus(String.format("%d downloads (%d active)", statuses.size(), active));

        updateButtonStates();
    }

    private void updateButtonStates() {
        int row = downloadTable.getSelectedRow();
        if (row < 0 || row >= tableModel.getRowCount()) {
            pauseButton.setEnabled(false);
            resumeButton.setEnabled(false);
            cancelButton.setEnabled(false);
            return;
        }

        String state = (String) tableModel.getValueAt(row, COL_STATE);
        pauseButton.setEnabled("Running".equals(state));
        resumeButton.setEnabled("Paused".equals(state));
        cancelButton.setEnabled("Running".equals(state) || "Paused".equals(state));
    }

    private String getSelectedTorrentId() {
        int row = downloadTable.getSelectedRow();
        if (row < 0 || row >= tableModel.getRowCount()) return null;
        return (String) tableModel.getValueAt(row, COL_ID);
    }

    // -- Utility --

    private void checkServerConnection() {
        new Thread(() -> {
            boolean available = apiService.isServerAvailable();
            SwingUtilities.invokeLater(() -> {
                if (available) {
                    log("Connected to BitTorrent engine.");
                    setStatus("Connected to engine");
                } else {
                    log("WARNING: Cannot reach BitTorrent engine at localhost:5000");
                    log("Make sure the Python server is running: python -m python_engine.api_server");
                    setStatus("Engine not available");
                }
            });
        }).start();
    }

    private void log(String message) {
        SwingUtilities.invokeLater(() -> {
            String timestamp = java.time.LocalTime.now()
                    .format(java.time.format.DateTimeFormatter.ofPattern("HH:mm:ss"));
            logArea.append("[" + timestamp + "] " + message + "\n");
            logArea.setCaretPosition(logArea.getDocument().getLength());
        });
    }

    private void setStatus(String text) {
        statusLabel.setText(" " + text);
    }

    private static String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024));
        return String.format("%.2f GB", bytes / (1024.0 * 1024 * 1024));
    }

    private static String formatSpeed(double bytesPerSec) {
        if (bytesPerSec < 1024) return String.format("%.0f B/s", bytesPerSec);
        if (bytesPerSec < 1024 * 1024) return String.format("%.1f KB/s", bytesPerSec / 1024);
        return String.format("%.1f MB/s", bytesPerSec / (1024 * 1024));
    }

    private void shutdown() {
        scheduler.shutdown();
        dispose();
        System.exit(0);
    }

    /**
     * Custom cell renderer that displays a progress bar in the table.
     */
    static class ProgressBarRenderer extends DefaultTableCellRenderer {
        private final JProgressBar progressBar = new JProgressBar(0, 100);

        public ProgressBarRenderer() {
            progressBar.setStringPainted(true);
        }

        @Override
        public Component getTableCellRendererComponent(JTable table, Object value,
                                                       boolean isSelected, boolean hasFocus,
                                                       int row, int column) {
            double progress = 0.0;
            if (value instanceof Double) {
                progress = (Double) value;
            }
            progressBar.setValue((int) progress);
            progressBar.setString(String.format("%.1f%%", progress));

            if (progress >= 100) {
                progressBar.setForeground(new Color(50, 150, 50));
            } else {
                progressBar.setForeground(new Color(60, 120, 200));
            }

            return progressBar;
        }
    }

    /**
     * Application entry point.
     */
    public static void main(String[] args) {
        // Set system look and feel
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            // Fallback to default
        }

        SwingUtilities.invokeLater(() -> {
            TorrentClientGUI gui = new TorrentClientGUI();
            gui.setVisible(true);
        });
    }
}
