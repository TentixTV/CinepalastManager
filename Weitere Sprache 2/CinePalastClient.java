import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class CinePalastClient {

    public static class MediaItem {
        public int id;
        public String name;
        public Integer jahr;
        public String schauspieler;
        public String genre;
        public Integer laufzeitMin;
        public String beschreibung;
        public String fsk;
        public String produktionsfirma;
        public String regisseur;
        public String filmreihe;
        public String produktionsland;
        public String deutscheSynchronsprecher;
        public String posterPfad;
        public String bannerPfad;
    }

    private final String dbUrl;

    public CinePalastClient(String dbPath) {
        this.dbUrl = "jdbc:sqlite:" + dbPath;
    }

    public List<MediaItem> getAllMovies() throws Exception {
        return searchMovies("", "Alles");
    }

    public List<MediaItem> searchMovies(String query, String filter) throws Exception {
        List<MediaItem> movies = new ArrayList<>();
        
        // Load SQLite JDBC Driver
        Class.forName("org.sqlite.JDBC");
        
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            String sql;
            if (query == null || query.trim().isEmpty()) {
                sql = "SELECT * FROM media ORDER BY Name ASC;";
            } else if ("Film".equals(filter)) {
                sql = "SELECT * FROM media WHERE Name LIKE ? OR Filmreihe LIKE ? ORDER BY Name ASC;";
            } else if ("Schauspieler".equals(filter)) {
                sql = "SELECT * FROM media WHERE Schauspieler LIKE ? ORDER BY Name ASC;";
            } else if ("Regisseur".equals(filter)) {
                sql = "SELECT * FROM media WHERE Regisseur LIKE ? ORDER BY Name ASC;";
            } else {
                sql = "SELECT * FROM media WHERE Name LIKE ? OR Schauspieler LIKE ? OR Genre LIKE ? OR Regisseur LIKE ? OR Filmreihe LIKE ? ORDER BY Name ASC;";
            }
            
            try (java.sql.PreparedStatement pstmt = conn.prepareStatement(sql)) {
                if (query != null && !query.trim().isEmpty()) {
                    String likeQuery = "%" + query + "%";
                    if ("Film".equals(filter)) {
                        pstmt.setString(1, likeQuery);
                        pstmt.setString(2, likeQuery);
                    } else if ("Schauspieler".equals(filter)) {
                        pstmt.setString(1, likeQuery);
                    } else if ("Regisseur".equals(filter)) {
                        pstmt.setString(1, likeQuery);
                    } else {
                        pstmt.setString(1, likeQuery);
                        pstmt.setString(2, likeQuery);
                        pstmt.setString(3, likeQuery);
                        pstmt.setString(4, likeQuery);
                        pstmt.setString(5, likeQuery);
                    }
                }
                
                try (ResultSet rs = pstmt.executeQuery()) {
                    while (rs.next()) {
                        MediaItem item = new MediaItem();
                        item.id = rs.getInt("ID");
                        item.name = rs.getString("Name");
                        
                        int j = rs.getInt("Jahr");
                        item.jahr = rs.wasNull() ? null : j;
                        
                        item.schauspieler = rs.getString("Schauspieler");
                        item.genre = rs.getString("Genre");
                        
                        int l = rs.getInt("Laufzeit_min");
                        item.laufzeitMin = rs.wasNull() ? null : l;
                        
                        item.beschreibung = rs.getString("Beschreibung");
                        item.fsk = rs.getString("FSK");
                        item.produktionsfirma = rs.getString("Produktionsfirma");
                        item.regisseur = rs.getString("Regisseur");
                        item.filmreihe = rs.getString("Filmreihe");
                        item.produktionsland = rs.getString("Produktionsland");
                        item.deutscheSynchronsprecher = rs.getString("Deutsche_Synchronsprecher");
                        item.posterPfad = rs.getString("Poster_Pfad");
                        item.bannerPfad = rs.getString("Banner_Pfad");
                        
                        movies.add(item);
                    }
                }
            }
        }
        return movies;
    }

    public static void Main(String[] args) {
        // Alias Main for console run
        main(args);
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Fehler: dbPath ist erforderlich.");
            System.out.println("Verwendung: CinePalastClient <dbPath> [query] [filter]");
            return;
        }
        String dbPath = args[0];
        String searchQuery = args.length > 1 ? args[1] : "";
        String searchFilter = args.length > 2 ? args[2] : "Alles";

        System.out.println("==================================================");
        System.out.println("CinePalast Manager — Java Datenbank Client");
        System.out.println("Verbindung mit Datenbank: " + dbPath);
        if (!searchQuery.isEmpty()) {
            System.out.println("Suchbegriff:            \"" + searchQuery + "\" (Filter: " + searchFilter + ")");
        }
        System.out.println("==================================================");

        try {
            CinePalastClient client = new CinePalastClient(dbPath);
            List<MediaItem> movies = client.searchMovies(searchQuery, searchFilter);

            System.out.println("\nGefundene Filme: " + movies.size() + "\n");

            for (MediaItem m : movies) {
                System.out.println("[" + m.id + "] " + m.name + " (" + (m.jahr != null ? m.jahr : "N/A") + ")");
                if (m.regisseur != null && !m.regisseur.isEmpty()) {
                    System.out.println("    Regisseur: " + m.regisseur);
                }
                if (m.genre != null && !m.genre.isEmpty()) {
                    System.out.println("    Genre:     " + m.genre);
                }
                if (m.schauspieler != null && !m.schauspieler.isEmpty()) {
                    System.out.println("    Cast:      " + m.schauspieler);
                }
                System.out.println("    ------------------------------------------");
            }
        } catch (Exception ex) {
            System.err.println("Fehler beim Lesen der Datenbank: " + ex.getMessage());
            ex.printStackTrace();
        }
    }
}
