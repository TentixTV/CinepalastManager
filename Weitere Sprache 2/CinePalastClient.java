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
        List<MediaItem> movies = new ArrayList<>();
        
        // Load SQLite JDBC Driver
        Class.forName("org.sqlite.JDBC");
        
        try (Connection conn = DriverManager.getConnection(dbUrl);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT * FROM media ORDER BY Name ASC;")) {
            
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
        return movies;
    }

    public static void Main(String[] args) {
        // Alias Main for console run
        main(args);
    }

    public static void main(String[] args) {
        String dbPath = args.length > 0 ? args[0] : "../CinePalast/cinepalast.db";

        System.out.println("==================================================");
        System.out.println("CinePalast Manager — Java Datenbank Client");
        System.out.println("Verbindung mit Datenbank: " + dbPath);
        System.out.println("==================================================");

        try {
            CinePalastClient client = new CinePalastClient(dbPath);
            List<MediaItem> movies = client.getAllMovies();

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
