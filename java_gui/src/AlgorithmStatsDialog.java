import org.json.JSONArray;
import org.json.JSONObject;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.util.ArrayList;
import java.util.List;

/**
 * Dialog showing algorithm statistics visualization:
 *  - Tab 1: Bar chart of Rarest-First piece selection distribution for a chosen torrent
 *  - Tab 2: General lifetime statistics across all downloads
 */
public class AlgorithmStatsDialog extends JDialog {

    private final ApiService apiService;

    // Tab 1 — piece selection
    private JComboBox<TorrentEntry> torrentPicker;
    private BarChartPanel barChartPanel;
    private JLabel summaryLabel;
    private List<TorrentEntry> torrentEntries = new ArrayList<>();

    // Tab 2 — general statistics
    private JLabel[] statValueLabels;
    private static final String[] STAT_NAMES = {
        "Total Files Downloaded",
        "Total Data Downloaded",
        "Total Download Time",
        "Average Download Speed",
        "Best Peak Speed",
        "Total Peers Connected",
        "Total Choke/Unchoke Cycles",
        "Largest File",
        "Fastest Download"
    };

    // ── Constructor ───────────────────────────────────────────────────────────

    public AlgorithmStatsDialog(Frame owner, ApiService apiService) {
        super(owner, "Algorithm Statistics", false);
        this.apiService = apiService;

        setSize(800, 560);
        setMinimumSize(new Dimension(640, 440));
        setLocationRelativeTo(owner);
        setLayout(new BorderLayout());

        JTabbedPane tabs = new JTabbedPane();
        tabs.addTab("Piece Selection (Rarest-First)", buildPieceTab());
        tabs.addTab("General Statistics", buildGeneralStatsTab());
        add(tabs, BorderLayout.CENTER);

        // Close button at bottom
        JPanel bottom = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        JButton closeBtn = new JButton("Close");
        closeBtn.addActionListener((ActionEvent e) -> dispose());
        bottom.add(closeBtn);
        add(bottom, BorderLayout.SOUTH);

        // Load data in background
        loadData();
    }

    // ── Tab builders ──────────────────────────────────────────────────────────

    private JPanel buildPieceTab() {
        JPanel panel = new JPanel(new BorderLayout(6, 6));
        panel.setBorder(new EmptyBorder(8, 8, 8, 8));

        // North: torrent picker
        JPanel pickerRow = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 0));
        pickerRow.add(new JLabel("Torrent:"));
        torrentPicker = new JComboBox<>();
        torrentPicker.setPreferredSize(new Dimension(320, 26));
        torrentPicker.addActionListener(e -> onTorrentSelected());
        pickerRow.add(torrentPicker);

        JButton refreshBtn = new JButton("Refresh");
        refreshBtn.addActionListener(e -> loadData());
        pickerRow.add(refreshBtn);
        panel.add(pickerRow, BorderLayout.NORTH);

        // Centre: custom bar chart — always fits within window width
        barChartPanel = new BarChartPanel();
        panel.add(barChartPanel, BorderLayout.CENTER);

        // South: summary text
        summaryLabel = new JLabel(" ");
        summaryLabel.setBorder(new EmptyBorder(4, 4, 0, 0));
        panel.add(summaryLabel, BorderLayout.SOUTH);

        return panel;
    }

    private JPanel buildGeneralStatsTab() {
        JPanel panel = new JPanel(new BorderLayout(6, 6));
        panel.setBorder(new EmptyBorder(12, 12, 12, 12));

        // Top row: Refresh + Clear History
        JPanel topRow = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 0));
        JButton refreshBtn = new JButton("Refresh");
        refreshBtn.addActionListener(e -> loadData());
        topRow.add(refreshBtn);
        JButton clearBtn = new JButton("Clear History");
        clearBtn.addActionListener(e -> {
            int choice = JOptionPane.showConfirmDialog(this,
                    "Clear all download history?", "Confirm",
                    JOptionPane.YES_NO_OPTION);
            if (choice == JOptionPane.YES_OPTION) {
                new Thread(() -> {
                    try {
                        apiService.clearHistory();
                        SwingUtilities.invokeLater(() -> {
                            torrentEntries.clear();
                            torrentPicker.removeAllItems();
                            barChartPanel.setData(null, null);
                            summaryLabel.setText("History cleared.");
                            resetGeneralStats();
                        });
                    } catch (Exception ex) {
                        SwingUtilities.invokeLater(() ->
                                summaryLabel.setText("Error clearing history: " + ex.getMessage()));
                    }
                }).start();
            }
        });
        topRow.add(clearBtn);
        panel.add(topRow, BorderLayout.NORTH);

        // Stats grid
        JPanel grid = new JPanel(new GridBagLayout());
        grid.setBackground(Color.WHITE);
        grid.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(200, 200, 200)),
                new EmptyBorder(16, 20, 16, 20)));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(8, 8, 8, 8);

        statValueLabels = new JLabel[STAT_NAMES.length];

        for (int i = 0; i < STAT_NAMES.length; i++) {
            gbc.gridx = 0;
            gbc.gridy = i;
            gbc.weightx = 0.4;
            gbc.anchor = GridBagConstraints.WEST;

            JLabel nameLabel = new JLabel(STAT_NAMES[i] + ":");
            nameLabel.setFont(nameLabel.getFont().deriveFont(Font.BOLD, 13f));
            nameLabel.setForeground(new Color(60, 60, 60));
            grid.add(nameLabel, gbc);

            gbc.gridx = 1;
            gbc.weightx = 0.6;

            statValueLabels[i] = new JLabel("—");
            statValueLabels[i].setFont(statValueLabels[i].getFont().deriveFont(Font.PLAIN, 13f));
            statValueLabels[i].setForeground(new Color(40, 40, 40));
            grid.add(statValueLabels[i], gbc);
        }

        // Add separator line before "notable" stats
        JPanel wrapper = new JPanel(new BorderLayout());
        wrapper.setBackground(Color.WHITE);
        wrapper.add(grid, BorderLayout.NORTH);
        panel.add(new JScrollPane(wrapper), BorderLayout.CENTER);

        return panel;
    }

    // ── Data loading ──────────────────────────────────────────────────────────

    private void loadData() {
        new Thread(() -> {
            try {
                JSONArray summary = apiService.getStatsSummary();
                SwingUtilities.invokeLater(() -> populateSummary(summary));
            } catch (Exception ex) {
                SwingUtilities.invokeLater(() ->
                        summaryLabel.setText("Error loading data: " + ex.getMessage()));
            }
        }).start();
    }

    private void populateSummary(JSONArray summary) {
        torrentEntries.clear();

        for (int i = 0; i < summary.length(); i++) {
            JSONObject row = summary.getJSONObject(i);
            String id   = row.optString("id");
            String name = row.optString("name", "Unknown");
            torrentEntries.add(new TorrentEntry(id, name));
        }

        // Refresh torrent picker (preserve selection)
        Object prev = torrentPicker.getSelectedItem();
        torrentPicker.removeAllItems();
        for (TorrentEntry e : torrentEntries) torrentPicker.addItem(e);
        if (prev != null) torrentPicker.setSelectedItem(prev);

        if (torrentPicker.getItemCount() == 0) {
            barChartPanel.setData(null, null);
            summaryLabel.setText("No completed downloads yet.");
        } else if (torrentPicker.getSelectedIndex() < 0) {
            torrentPicker.setSelectedIndex(0);
        } else {
            onTorrentSelected();
        }

        // Update general statistics tab
        updateGeneralStats(summary);
    }

    private void onTorrentSelected() {
        TorrentEntry entry = (TorrentEntry) torrentPicker.getSelectedItem();
        if (entry == null) return;

        new Thread(() -> {
            try {
                JSONArray pieceStats = apiService.getAlgorithmStats(entry.id);
                SwingUtilities.invokeLater(() -> displayPieceChart(entry.name, pieceStats));
            } catch (Exception ex) {
                SwingUtilities.invokeLater(() ->
                        summaryLabel.setText("Error: " + ex.getMessage()));
            }
        }).start();
    }

    private void displayPieceChart(String torrentName, JSONArray pieceStats) {
        if (pieceStats.length() == 0) {
            barChartPanel.setData(null, torrentName);
            summaryLabel.setText(torrentName + " — No Rarest-First data (Random algorithm may have been used)");
            return;
        }

        // Build sorted piece-index -> selection-count list
        int maxIdx = 0;
        for (int i = 0; i < pieceStats.length(); i++) {
            maxIdx = Math.max(maxIdx, pieceStats.getJSONObject(i).optInt("piece_index", 0));
        }

        List<Integer> counts = new ArrayList<>();
        int ptr = 0;
        long totalSelections = 0;
        for (int idx = 0; idx <= maxIdx; idx++) {
            int count = 0;
            if (ptr < pieceStats.length()) {
                JSONObject row = pieceStats.getJSONObject(ptr);
                if (row.optInt("piece_index", -1) == idx) {
                    count = row.optInt("selected_as_rarest", 0);
                    ptr++;
                }
            }
            counts.add(count);
            totalSelections += count;
        }

        int totalPieces = maxIdx + 1;
        double avg = totalPieces > 0 ? (double) totalSelections / totalPieces : 0;
        summaryLabel.setText(String.format(
                "%s  |  Pieces: %d  |  Total Rarest-First selections: %d  |  Avg: %.2f",
                torrentName, totalPieces, totalSelections, avg));

        barChartPanel.setData(counts, torrentName);
    }

    // ── General Statistics ────────────────────────────────────────────────────

    private void updateGeneralStats(JSONArray summary) {
        if (summary.length() == 0) {
            resetGeneralStats();
            return;
        }

        int totalFiles = summary.length();
        long totalDataBytes = 0;
        int totalTimeSec = 0;
        double bestPeak = 0;
        int totalPeers = 0;
        int totalChokeCycles = 0;
        String largestName = "—"; long largestSize = 0;
        String fastestName = "—"; double fastestSpeed = 0;

        for (int i = 0; i < summary.length(); i++) {
            JSONObject row = summary.getJSONObject(i);
            long size      = row.optLong("size", 0);
            int timeSec    = row.optInt("total_time_seconds", 0);
            double avgSpd  = row.optDouble("avg_speed", 0);
            double pkSpd   = row.optDouble("peak_speed", 0);
            int peers      = row.optInt("avg_peers", 0);
            int cycles     = row.optInt("choke_cycles", 0);
            String name    = row.optString("name", "Unknown");

            totalDataBytes += size;
            totalTimeSec   += timeSec;
            if (pkSpd > bestPeak) bestPeak = pkSpd;
            totalPeers     += peers;
            totalChokeCycles += cycles;
            if (size > largestSize) { largestSize = size; largestName = name; }
            if (avgSpd > fastestSpeed) { fastestSpeed = avgSpd; fastestName = name; }
        }

        double avgSpeed = totalTimeSec > 0 ? (double) totalDataBytes / totalTimeSec : 0;

        statValueLabels[0].setText(String.valueOf(totalFiles));
        statValueLabels[1].setText(formatSize(totalDataBytes));
        statValueLabels[2].setText(formatDurationLong(totalTimeSec));
        statValueLabels[3].setText(formatSpeed(avgSpeed));
        statValueLabels[4].setText(formatSpeed(bestPeak));
        statValueLabels[5].setText(String.valueOf(totalPeers));
        statValueLabels[6].setText(String.valueOf(totalChokeCycles));
        statValueLabels[7].setText(largestSize > 0
                ? largestName + " (" + formatSize(largestSize) + ")"
                : "—");
        statValueLabels[8].setText(fastestSpeed > 0
                ? fastestName + " (" + formatSpeed(fastestSpeed) + ")"
                : "—");
    }

    private void resetGeneralStats() {
        for (JLabel label : statValueLabels) {
            label.setText("—");
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static String friendlyAlgo(String raw) {
        if (raw == null) return "—";
        switch (raw) {
            case "rarest_first": return "Rarest-First";
            case "random":       return "Random";
            case "tit_for_tat":  return "Tit-for-Tat";
            case "round_robin":  return "Round-Robin";
            default:             return raw;
        }
    }

    private static String formatDuration(int seconds) {
        if (seconds <= 0) return "—";
        if (seconds < 60) return seconds + "s";
        return String.format("%dm %ds", seconds / 60, seconds % 60);
    }

    private static String formatDurationLong(int seconds) {
        if (seconds <= 0) return "—";
        if (seconds < 60) return seconds + "s";
        if (seconds < 3600) return String.format("%dm %ds", seconds / 60, seconds % 60);
        return String.format("%dh %dm %ds", seconds / 3600, (seconds % 3600) / 60, seconds % 60);
    }

    private static String formatSpeed(double bytesPerSec) {
        if (bytesPerSec <= 0)         return "—";
        if (bytesPerSec < 1024)       return String.format("%.0f B/s",  bytesPerSec);
        if (bytesPerSec < 1024*1024)  return String.format("%.1f KB/s", bytesPerSec / 1024);
        return                               String.format("%.1f MB/s", bytesPerSec / (1024*1024));
    }

    private static String formatSize(long bytes) {
        if (bytes <= 0)                    return "0 B";
        if (bytes < 1024)                  return bytes + " B";
        if (bytes < 1024 * 1024)           return String.format("%.1f KB", bytes / 1024.0);
        if (bytes < 1024L * 1024 * 1024)   return String.format("%.1f MB", bytes / (1024.0 * 1024));
        return                                    String.format("%.2f GB", bytes / (1024.0 * 1024 * 1024));
    }

    // ── Inner classes ─────────────────────────────────────────────────────────

    /** Simple value-object for torrent picker entries. */
    private static class TorrentEntry {
        final String id;
        final String name;
        TorrentEntry(String id, String name) { this.id = id; this.name = name; }
        @Override public String toString() { return name; }
        @Override public boolean equals(Object o) {
            return (o instanceof TorrentEntry) && id.equals(((TorrentEntry) o).id);
        }
        @Override public int hashCode() { return id.hashCode(); }
    }

    /**
     * Custom panel that draws a vertical bar chart using Java2D.
     * Automatically aggregates pieces into buckets when there are too many
     * to display individually, so the chart always fits the window width.
     */
    static class BarChartPanel extends JPanel {

        private static final int MARGIN_LEFT   = 55;
        private static final int MARGIN_RIGHT  = 15;
        private static final int MARGIN_TOP    = 30;
        private static final int MARGIN_BOTTOM = 40;
        private static final int Y_TICKS       = 5;
        private static final int MAX_BARS      = 40;   // max bars to draw
        private static final int MIN_BAR_WIDTH = 8;    // minimum pixels per bar
        private static final Color BAR_COLOR   = new Color(70, 130, 180);   // steel blue
        private static final Color GRID_COLOR  = new Color(210, 210, 210);

        private List<Integer> rawData;      // one entry per piece index
        private List<Integer> bucketData;   // aggregated bucket sums
        private List<String>  bucketLabels; // label for each bucket
        private String title;

        BarChartPanel() {
            setBackground(Color.WHITE);
        }

        void setData(List<Integer> data, String torrentTitle) {
            this.rawData = data;
            this.title   = torrentTitle;
            aggregateIntoBuckets();
            repaint();
        }

        /** Aggregate raw per-piece data into displayable buckets. */
        private void aggregateIntoBuckets() {
            if (rawData == null || rawData.isEmpty()) {
                bucketData   = null;
                bucketLabels = null;
                return;
            }

            int n = rawData.size();
            // Determine number of buckets: at most MAX_BARS, at least 1
            int chartW = Math.max(200, getWidth() - MARGIN_LEFT - MARGIN_RIGHT);
            int maxByWidth = chartW / MIN_BAR_WIDTH;
            int numBuckets = Math.min(n, Math.min(MAX_BARS, Math.max(1, maxByWidth)));

            bucketData   = new ArrayList<>(numBuckets);
            bucketLabels = new ArrayList<>(numBuckets);

            int piecesPerBucket = (int) Math.ceil((double) n / numBuckets);

            for (int b = 0; b < numBuckets; b++) {
                int start = b * piecesPerBucket;
                int end   = Math.min(start + piecesPerBucket, n);
                int sum   = 0;
                for (int i = start; i < end; i++) {
                    sum += rawData.get(i);
                }
                bucketData.add(sum);
                if (piecesPerBucket == 1) {
                    bucketLabels.add(String.valueOf(start));
                } else {
                    bucketLabels.add(start + "-" + (end - 1));
                }
            }
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g;
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

            int W = getWidth();
            int H = getHeight();

            // Re-aggregate if window was resized since last setData
            if (rawData != null && !rawData.isEmpty()) {
                aggregateIntoBuckets();
            }

            // Title
            if (title != null) {
                g2.setColor(Color.DARK_GRAY);
                g2.setFont(g2.getFont().deriveFont(Font.BOLD, 12f));
                FontMetrics fm = g2.getFontMetrics();
                String t = "Rarest-First Piece Selection — " + title;
                g2.drawString(t, (W - fm.stringWidth(t)) / 2, MARGIN_TOP - 8);
            }

            if (bucketData == null || bucketData.isEmpty()) {
                g2.setColor(Color.GRAY);
                g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 13f));
                String msg = "No data to display";
                FontMetrics fm = g2.getFontMetrics();
                g2.drawString(msg, (W - fm.stringWidth(msg)) / 2, H / 2);
                return;
            }

            int chartW = W - MARGIN_LEFT - MARGIN_RIGHT;
            int chartH = H - MARGIN_TOP  - MARGIN_BOTTOM;
            if (chartW < 10 || chartH < 10) return;

            int n      = bucketData.size();
            int maxVal = bucketData.stream().mapToInt(Integer::intValue).max().orElse(1);

            // Y-axis label
            boolean bucketed = rawData != null && rawData.size() > n;
            String yLabel = bucketed ? "Selections (sum per group)" : "Selection Count";
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 10f));

            // Draw grid lines + Y-axis labels
            FontMetrics fm = g2.getFontMetrics();
            for (int t = 0; t <= Y_TICKS; t++) {
                int yVal  = (int) Math.round((double) maxVal * t / Y_TICKS);
                int yPx   = MARGIN_TOP + chartH - (int) ((double) chartH * t / Y_TICKS);
                g2.setColor(GRID_COLOR);
                g2.drawLine(MARGIN_LEFT, yPx, MARGIN_LEFT + chartW, yPx);
                g2.setColor(Color.DARK_GRAY);
                String label = String.valueOf(yVal);
                g2.drawString(label, MARGIN_LEFT - fm.stringWidth(label) - 4, yPx + fm.getAscent() / 2);
            }

            // Draw bars — guarantee at least 2px gap between bars
            int gap  = Math.max(2, chartW / (n * 5));
            int barW = Math.max(4, (chartW - gap * (n + 1)) / n);
            int totalUsed = barW * n + gap * (n + 1);
            int offsetX = (chartW - totalUsed) / 2;  // centre bars
            for (int i = 0; i < n; i++) {
                int val  = bucketData.get(i);
                if (val <= 0) continue;
                int barH = Math.max(1, (int) ((double) chartH * val / maxVal));
                int x    = MARGIN_LEFT + offsetX + gap + i * (barW + gap);
                int y    = MARGIN_TOP + chartH - barH;
                g2.setColor(BAR_COLOR);
                g2.fillRect(x, y, barW, barH);
                g2.setColor(BAR_COLOR.darker());
                g2.drawRect(x, y, barW, barH);
            }

            // Draw axes
            g2.setColor(Color.DARK_GRAY);
            g2.setStroke(new BasicStroke(1.5f));
            g2.drawLine(MARGIN_LEFT, MARGIN_TOP, MARGIN_LEFT, MARGIN_TOP + chartH);
            g2.drawLine(MARGIN_LEFT, MARGIN_TOP + chartH, MARGIN_LEFT + chartW, MARGIN_TOP + chartH);

            // X-axis tick labels — show ~10 evenly spaced
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 9f));
            fm = g2.getFontMetrics();
            int tickCount = Math.min(n, 10);
            int prevLabelEnd = -1; // avoid overlap
            for (int t = 0; t < tickCount; t++) {
                int idx = (int) Math.round((double) (n - 1) * t / Math.max(1, tickCount - 1));
                if (idx < 0 || idx >= n) continue;
                int xPx = MARGIN_LEFT + offsetX + gap + idx * (barW + gap) + barW / 2;
                String lbl = bucketLabels.get(idx);
                int lblW = fm.stringWidth(lbl);
                int lblX = xPx - lblW / 2;
                // Only draw if it fits and doesn't overlap previous label
                if (lblX >= MARGIN_LEFT && lblX > prevLabelEnd + 4
                        && xPx + lblW / 2 <= W - MARGIN_RIGHT) {
                    g2.setColor(Color.DARK_GRAY);
                    g2.drawString(lbl, lblX, MARGIN_TOP + chartH + fm.getAscent() + 4);
                    prevLabelEnd = lblX + lblW;
                }
            }

            // X-axis label
            String xLabel = bucketed ? "Piece Index (grouped)" : "Piece Index";
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 11f));
            fm = g2.getFontMetrics();
            g2.setColor(Color.DARK_GRAY);
            g2.drawString(xLabel, MARGIN_LEFT + (chartW - fm.stringWidth(xLabel)) / 2, H - 6);
        }
    }
}
