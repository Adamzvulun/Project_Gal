import org.json.JSONArray;
import org.json.JSONObject;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.util.ArrayList;
import java.util.List;

/**
 * Dialog showing algorithm statistics visualization:
 *  - Tab 1: Bar chart of Rarest-First piece selection distribution for a chosen torrent
 *  - Tab 2: Performance comparison table across all completed downloads
 */
public class AlgorithmStatsDialog extends JDialog {

    private final ApiService apiService;

    // Tab 1 — piece selection
    private JComboBox<TorrentEntry> torrentPicker;
    private BarChartPanel barChartPanel;
    private JLabel summaryLabel;
    private List<TorrentEntry> torrentEntries = new ArrayList<>();

    // Tab 2 — comparison table
    private DefaultTableModel compTableModel;

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
        tabs.addTab("Performance Comparison", buildComparisonTab());
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

        // Centre: custom bar chart
        barChartPanel = new BarChartPanel();
        panel.add(new JScrollPane(barChartPanel,
                JScrollPane.VERTICAL_SCROLLBAR_NEVER,
                JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED), BorderLayout.CENTER);

        // South: summary text
        summaryLabel = new JLabel(" ");
        summaryLabel.setBorder(new EmptyBorder(4, 4, 0, 0));
        panel.add(summaryLabel, BorderLayout.SOUTH);

        return panel;
    }

    private JPanel buildComparisonTab() {
        JPanel panel = new JPanel(new BorderLayout(6, 6));
        panel.setBorder(new EmptyBorder(8, 8, 8, 8));

        String[] cols = {"Name", "Piece Algo", "Peer Algo",
                "Avg Speed", "Peak Speed", "Time (sec)",
                "Choke", "Unchoke", "Status"};
        compTableModel = new DefaultTableModel(cols, 0) {
            @Override public boolean isCellEditable(int r, int c) { return false; }
        };
        JTable table = new JTable(compTableModel);
        table.setAutoResizeMode(JTable.AUTO_RESIZE_ALL_COLUMNS);
        table.getTableHeader().setReorderingAllowed(false);

        panel.add(new JScrollPane(table), BorderLayout.CENTER);
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
        // Populate comparison table
        compTableModel.setRowCount(0);
        torrentEntries.clear();

        for (int i = 0; i < summary.length(); i++) {
            JSONObject row = summary.getJSONObject(i);

            String id     = row.optString("id");
            String name   = row.optString("name", "Unknown");
            String pAlgo  = friendlyAlgo(row.optString("piece_algorithm", "rarest_first"));
            String eAlgo  = friendlyAlgo(row.optString("peer_algorithm",  "tit_for_tat"));
            double avgSpd = row.optDouble("avg_speed",  0);
            double pkSpd  = row.optDouble("peak_speed", 0);
            int    time   = row.optInt("total_time_seconds", 0);
            int    choke  = row.optInt("choke_count",   0);
            int    unchoke= row.optInt("unchoke_count", 0);
            String status = row.optString("final_status", "-");

            compTableModel.addRow(new Object[]{
                    name, pAlgo, eAlgo,
                    formatSpeed(avgSpd), formatSpeed(pkSpd),
                    time, choke, unchoke, status
            });

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

        // Build sorted piece-index → selection-count list
        // pieceStats is already ordered by piece_index
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

    private static String formatSpeed(double bytesPerSec) {
        if (bytesPerSec <= 0)         return "—";
        if (bytesPerSec < 1024)       return String.format("%.0f B/s",  bytesPerSec);
        if (bytesPerSec < 1024*1024)  return String.format("%.1f KB/s", bytesPerSec / 1024);
        return                               String.format("%.1f MB/s", bytesPerSec / (1024*1024));
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
     * No external charting library is required.
     */
    static class BarChartPanel extends JPanel {

        private static final int MARGIN_LEFT   = 55;
        private static final int MARGIN_RIGHT  = 15;
        private static final int MARGIN_TOP    = 30;
        private static final int MARGIN_BOTTOM = 40;
        private static final int Y_TICKS       = 5;
        private static final Color BAR_COLOR   = new Color(70, 130, 180);   // steel blue
        private static final Color GRID_COLOR  = new Color(210, 210, 210);

        private List<Integer> data;    // one entry per piece index
        private String title;

        BarChartPanel() {
            setBackground(Color.WHITE);
            setPreferredSize(new Dimension(600, 300));
        }

        void setData(List<Integer> data, String torrentTitle) {
            this.data  = data;
            this.title = torrentTitle;
            // Widen preferred width proportionally when there are many pieces
            if (data != null && !data.isEmpty()) {
                int minW = Math.max(600, data.size() * 4 + MARGIN_LEFT + MARGIN_RIGHT);
                setPreferredSize(new Dimension(minW, 300));
            }
            revalidate();
            repaint();
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g;
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

            int W = getWidth();
            int H = getHeight();

            // Title
            if (title != null) {
                g2.setColor(Color.DARK_GRAY);
                g2.setFont(g2.getFont().deriveFont(Font.BOLD, 12f));
                FontMetrics fm = g2.getFontMetrics();
                String t = "Rarest-First — " + title;
                g2.drawString(t, (W - fm.stringWidth(t)) / 2, MARGIN_TOP - 8);
            }

            if (data == null || data.isEmpty()) {
                g2.setColor(Color.GRAY);
                g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 13f));
                String msg = "No data to display";
                FontMetrics fm = g2.getFontMetrics();
                g2.drawString(msg, (W - fm.stringWidth(msg)) / 2, H / 2);
                return;
            }

            int chartW = W - MARGIN_LEFT - MARGIN_RIGHT;
            int chartH = H - MARGIN_TOP  - MARGIN_BOTTOM;
            int n      = data.size();
            int maxVal = data.stream().mapToInt(Integer::intValue).max().orElse(1);

            // Draw grid lines + Y-axis labels
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 10f));
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

            // Draw bars
            double barW = (double) chartW / n;
            for (int i = 0; i < n; i++) {
                int val  = data.get(i);
                if (val <= 0) continue;
                int barH = (int) ((double) chartH * val / maxVal);
                int x    = MARGIN_LEFT + (int) (i * barW);
                int y    = MARGIN_TOP + chartH - barH;
                int bw   = Math.max(1, (int) barW - 1);
                g2.setColor(BAR_COLOR);
                g2.fillRect(x, y, bw, barH);
                g2.setColor(BAR_COLOR.darker());
                g2.drawRect(x, y, bw, barH);
            }

            // Draw axes
            g2.setColor(Color.DARK_GRAY);
            g2.setStroke(new BasicStroke(1.5f));
            g2.drawLine(MARGIN_LEFT, MARGIN_TOP, MARGIN_LEFT, MARGIN_TOP + chartH);           // Y
            g2.drawLine(MARGIN_LEFT, MARGIN_TOP + chartH, MARGIN_LEFT + chartW, MARGIN_TOP + chartH); // X

            // X-axis label
            String xLabel = "Piece Index";
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 11f));
            fm = g2.getFontMetrics();
            g2.drawString(xLabel, MARGIN_LEFT + (chartW - fm.stringWidth(xLabel)) / 2,
                    H - 6);

            // X tick labels (show a few evenly spaced)
            g2.setFont(g2.getFont().deriveFont(Font.PLAIN, 9f));
            fm = g2.getFontMetrics();
            int tickCount = Math.min(n, 10);
            for (int t = 0; t <= tickCount; t++) {
                int idx = (int) Math.round((double) (n - 1) * t / tickCount);
                int xPx = MARGIN_LEFT + (int) ((idx + 0.5) * barW);
                String lbl = String.valueOf(idx);
                g2.setColor(Color.DARK_GRAY);
                g2.drawString(lbl, xPx - fm.stringWidth(lbl) / 2,
                        MARGIN_TOP + chartH + fm.getAscent() + 4);
            }
        }
    }
}
