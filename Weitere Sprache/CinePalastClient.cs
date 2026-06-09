using System;
using System.Collections.Generic;
using Microsoft.Data.Sqlite;

namespace CinePalast
{
    public class MediaItem
    {
        public long ID { get; set; }
        public string Name { get; set; } = string.Empty;
        public int? Jahr { get; set; }
        public string? Schauspieler { get; set; }
        public string? Genre { get; set; }
        public int? LaufzeitMin { get; set; }
        public string? Beschreibung { get; set; }
        public string? FSK { get; set; }
        public string? Produktionsfirma { get; set; }
        public string? Regisseur { get; set; }
        public string? Filmreihe { get; set; }
        public string? Produktionsland { get; set; }
        public string? DeutscheSynchronsprecher { get; set; }
        public string? PosterPfad { get; set; }
        public string? BannerPfad { get; set; }
    }

    public class CinePalastClient
    {
        private readonly string _connectionString;

        public CinePalastClient(string dbPath)
        {
            _connectionString = $"Data Source={dbPath}";
        }

        public List<MediaItem> GetAllMovies()
        {
            return SearchMovies(string.Empty, "Alles");
        }

        public List<MediaItem> SearchMovies(string query, string filter = "Alles")
        {
            var movies = new List<MediaItem>();

            using (var connection = new SqliteConnection(_connectionString))
            {
                connection.Open();

                var command = connection.CreateCommand();
                string sql;
                string likeQuery = $"%{query}%";

                if (string.IsNullOrWhiteSpace(query))
                {
                    sql = "SELECT * FROM media ORDER BY Name ASC;";
                }
                else if (filter == "Film")
                {
                    sql = "SELECT * FROM media WHERE Name LIKE $query OR Filmreihe LIKE $query ORDER BY Name ASC;";
                    command.Parameters.AddWithValue("$query", likeQuery);
                }
                else if (filter == "Schauspieler")
                {
                    sql = "SELECT * FROM media WHERE Schauspieler LIKE $query ORDER BY Name ASC;";
                    command.Parameters.AddWithValue("$query", likeQuery);
                }
                else if (filter == "Regisseur")
                {
                    sql = "SELECT * FROM media WHERE Regisseur LIKE $query ORDER BY Name ASC;";
                    command.Parameters.AddWithValue("$query", likeQuery);
                }
                else
                {
                    sql = "SELECT * FROM media WHERE Name LIKE $query OR Schauspieler LIKE $query OR Genre LIKE $query OR Regisseur LIKE $query OR Filmreihe LIKE $query ORDER BY Name ASC;";
                    command.Parameters.AddWithValue("$query", likeQuery);
                }

                command.CommandText = sql;

                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var item = new MediaItem
                        {
                            ID = reader.GetInt64(reader.GetOrdinal("ID")),
                            Name = reader.GetString(reader.GetOrdinal("Name")),
                            Jahr = reader.IsDBNull(reader.GetOrdinal("Jahr")) ? null : (int?)reader.GetInt32(reader.GetOrdinal("Jahr")),
                            Schauspieler = reader.IsDBNull(reader.GetOrdinal("Schauspieler")) ? null : reader.GetString(reader.GetOrdinal("Schauspieler")),
                            Genre = reader.IsDBNull(reader.GetOrdinal("Genre")) ? null : reader.GetString(reader.GetOrdinal("Genre")),
                            LaufzeitMin = reader.IsDBNull(reader.GetOrdinal("Laufzeit_min")) ? null : (int?)reader.GetInt32(reader.GetOrdinal("Laufzeit_min")),
                            Beschreibung = reader.IsDBNull(reader.GetOrdinal("Beschreibung")) ? null : reader.GetString(reader.GetOrdinal("Beschreibung")),
                            FSK = reader.IsDBNull(reader.GetOrdinal("FSK")) ? null : reader.GetString(reader.GetOrdinal("FSK")),
                            Produktionsfirma = reader.IsDBNull(reader.GetOrdinal("Produktionsfirma")) ? null : reader.GetString(reader.GetOrdinal("Produktionsfirma")),
                            Regisseur = reader.IsDBNull(reader.GetOrdinal("Regisseur")) ? null : reader.GetString(reader.GetOrdinal("Regisseur")),
                            Filmreihe = reader.IsDBNull(reader.GetOrdinal("Filmreihe")) ? null : reader.GetString(reader.GetOrdinal("Filmreihe")),
                            Produktionsland = reader.IsDBNull(reader.GetOrdinal("Produktionsland")) ? null : reader.GetString(reader.GetOrdinal("Produktionsland")),
                            DeutscheSynchronsprecher = reader.IsDBNull(reader.GetOrdinal("Deutsche_Synchronsprecher")) ? null : reader.GetString(reader.GetOrdinal("Deutsche_Synchronsprecher")),
                            PosterPfad = reader.IsDBNull(reader.GetOrdinal("Poster_Pfad")) ? null : reader.GetString(reader.GetOrdinal("Poster_Pfad")),
                            BannerPfad = reader.IsDBNull(reader.GetOrdinal("Banner_Pfad")) ? null : reader.GetString(reader.GetOrdinal("Banner_Pfad"))
                        };
                        movies.Add(item);
                    }
                }
            }

            return movies;
        }

        public static void Main(string[] args)
        {
            string dbPath = args.Length > 0 ? args[0] : "../CinePalast/cinepalast.db";
            string searchQuery = args.Length > 1 ? args[1] : string.Empty;
            string searchFilter = args.Length > 2 ? args[2] : "Alles";
            
            Console.WriteLine("==================================================");
            Console.WriteLine("CinePalast Manager — C# Datenbank Client");
            Console.WriteLine($"Verbindung mit Datenbank: {dbPath}");
            if (!string.IsNullOrEmpty(searchQuery))
            {
                Console.WriteLine($"Suchbegriff:            \"{searchQuery}\" (Filter: {searchFilter})");
            }
            Console.WriteLine("==================================================");

            try
            {
                var client = new CinePalastClient(dbPath);
                var movies = client.SearchMovies(searchQuery, searchFilter);

                Console.WriteLine($"\nGefundene Filme: {movies.Count}\n");

                foreach (var m in movies)
                {
                    Console.WriteLine($"[{m.ID}] {m.Name} ({m.Jahr?.ToString() ?? "N/A"})");
                    if (!string.IsNullOrEmpty(m.Regisseur))
                        Console.WriteLine($"    Regisseur: {m.Regisseur}");
                    if (!string.IsNullOrEmpty(m.Genre))
                        Console.WriteLine($"    Genre:     {m.Genre}");
                    if (!string.IsNullOrEmpty(m.Schauspieler))
                        Console.WriteLine($"    Cast:      {m.Schauspieler}");
                    Console.WriteLine("    ------------------------------------------");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Fehler beim Lesen der Datenbank: {ex.Message}");
            }
        }
    }
}
