// --- State Management ---
let appState = {
    movies: [],
    viewMode: 'Galerie', // 'Galerie' or 'Tabelle'
    config: {},
    currentMovie: null,
    searchQuery: '',
    searchFilter: 'Alles'
};

// --- DOM References ---
const dom = {
    searchFilter: document.getElementById('search-filter'),
    searchInput: document.getElementById('search-input'),
    clearSearch: document.getElementById('clear-search'),
    viewGallery: document.getElementById('view-gallery'),
    viewTable: document.getElementById('view-table'),
    movieGrid: document.getElementById('movie-grid'),
    movieTableWrapper: document.getElementById('movie-table-wrapper'),
    movieTableBody: document.getElementById('movie-table-body'),
    emptyState: document.getElementById('empty-state'),
    btnEmptyOnlineSearch: document.getElementById('btn-empty-online-search'),
    btnAddMovie: document.getElementById('btn-add-movie'),
    btnSettings: document.getElementById('btn-settings'),
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingText: document.getElementById('loading-text')
};

// --- Initialization ---
window.addEventListener('DOMContentLoaded', () => {
    showLoading("Initialisiere CinePalast...");
    
    // Check if pywebview is loaded. If yes, init immediately, otherwise wait for its event.
    if (window.pywebview) {
        initApp();
    } else {
        window.addEventListener('pywebviewready', initApp);
    }
});

async function initApp() {
    try {
        // 1. Load config
        appState.config = await pywebview.api.load_config();
        
        // 2. Set theme
        applyTheme(appState.config.theme || 'cyan');
        
        // 3. Set view mode
        setViewMode(appState.config.default_view || 'Galerie');
        
        // 4. Set search filter dropdown
        dom.searchFilter.value = appState.searchFilter;
        
        // 5. Load and display movies
        await refreshMovies();
        
        // 6. Bind events
        bindEvents();
        
        hideLoading();
    } catch (e) {
        console.error("Init Error:", e);
        hideLoading();
    }
}

// --- Event Bindings ---
function bindEvents() {
    // Search input typing
    dom.searchInput.addEventListener('input', (e) => {
        appState.searchQuery = e.target.value;
        toggleClearSearchButton();
        performSearch();
    });

    // Clear search
    dom.clearSearch.addEventListener('click', () => {
        dom.searchInput.value = '';
        appState.searchQuery = '';
        toggleClearSearchButton();
        performSearch();
    });

    // Filter change
    dom.searchFilter.addEventListener('change', (e) => {
        appState.searchFilter = e.target.value;
        performSearch();
    });

    // View toggles
    dom.viewGallery.addEventListener('click', () => setViewMode('Galerie'));
    dom.viewTable.addEventListener('click', () => setViewMode('Tabelle'));

    // Main buttons
    dom.btnAddMovie.addEventListener('click', () => openMovieForm());
    dom.btnSettings.addEventListener('click', () => openSettings());
    
    // Online search from empty state
    dom.btnEmptyOnlineSearch.addEventListener('click', () => triggerOnlineSearch());
    
    // Settings browse path
    document.getElementById('btn-browse-path').addEventListener('click', browseCustomPath);
    document.getElementById('btn-test-keys').addEventListener('click', testAPIConnections);
    document.getElementById('btn-backup-db').addEventListener('click', backupDatabase);
    document.getElementById('btn-restore-db').addEventListener('click', restoreDatabase);
    document.getElementById('btn-reset-db').addEventListener('click', resetDatabase);
    
    // Movie Form browse assets
    document.getElementById('btn-browse-poster').addEventListener('click', () => browseAsset('poster'));
    document.getElementById('btn-browse-banner').addEventListener('click', () => browseAsset('banner'));
    
    // Movie details footer
    document.getElementById('btn-edit-current').addEventListener('click', () => {
        if (appState.currentMovie) {
            closeModal('modal-details');
            openMovieForm(appState.currentMovie);
        }
    });
    document.getElementById('btn-delete-current').addEventListener('click', () => {
        if (appState.currentMovie) {
            deleteMovie(appState.currentMovie.ID);
        }
    });
}

// --- Loading indicator ---
function showLoading(text = "Lade...") {
    dom.loadingText.innerText = text;
    dom.loadingOverlay.classList.add('active');
}

function hideLoading() {
    dom.loadingOverlay.classList.remove('active');
}

// --- Apply theme colors ---
function applyTheme(themeName) {
    document.body.className = '';
    document.body.classList.add(`theme-${themeName}`);
    document.getElementById('settings-theme').value = themeName;
}

// --- Toggle clear search button ---
function toggleClearSearchButton() {
    if (appState.searchQuery.length > 0) {
        dom.clearSearch.style.display = 'block';
    } else {
        dom.clearSearch.style.display = 'none';
    }
}

// --- Change active view mode ---
function setViewMode(mode) {
    appState.viewMode = mode;
    if (mode === 'Galerie') {
        dom.viewGallery.classList.add('active');
        dom.viewTable.classList.remove('active');
        dom.movieGrid.classList.add('active');
        dom.movieTableWrapper.classList.remove('active');
    } else {
        dom.viewGallery.classList.remove('active');
        dom.viewTable.classList.add('active');
        dom.movieGrid.classList.remove('active');
        dom.movieTableWrapper.classList.add('active');
    }
    renderMovies();
}

// --- Load movies from database ---
async function refreshMovies() {
    if (appState.searchQuery.trim().length > 0) {
        appState.movies = await pywebview.api.search_movies(appState.searchQuery, appState.searchFilter);
    } else {
        appState.movies = await pywebview.api.get_all_movies();
    }
    renderMovies();
}

// --- Perform realtime search ---
let searchDebounceTimeout;
function performSearch() {
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(async () => {
        showLoading("Suche in der Datenbank...");
        await refreshMovies();
        
        // If query is set but no local results, show "Online suchen" button
        if (appState.movies.length === 0 && appState.searchQuery.trim().length > 0) {
            dom.btnEmptyOnlineSearch.style.display = 'inline-flex';
        } else {
            dom.btnEmptyOnlineSearch.style.display = 'none';
        }
        hideLoading();
    }, 250);
}

// --- Render Movie Cards & Table Rows ---
function renderMovies() {
    dom.movieGrid.innerHTML = '';
    dom.movieTableBody.innerHTML = '';

    if (appState.movies.length === 0) {
        dom.emptyState.style.display = 'flex';
        dom.movieGrid.classList.remove('active');
        dom.movieTableWrapper.classList.remove('active');
        return;
    }

    dom.emptyState.style.display = 'none';
    if (appState.viewMode === 'Galerie') {
        dom.movieGrid.classList.add('active');
        dom.movieTableWrapper.classList.remove('active');
    } else {
        dom.movieGrid.classList.remove('active');
        dom.movieTableWrapper.classList.add('active');
    }

    appState.movies.forEach(movie => {
        // 1. Render Gallery Card
        const card = document.createElement('div');
        card.className = 'movie-card';
        card.addEventListener('click', () => showMovieDetails(movie));

        const imgContainer = document.createElement('div');
        imgContainer.className = 'movie-card-img-container';

        if (movie.Poster_Pfad) {
            const img = document.createElement('img');
            img.src = getMediaUrl(movie.Poster_Pfad);
            img.className = 'movie-card-img';
            img.alt = movie.Name;
            // Handle loading error
            img.onerror = () => {
                imgContainer.innerHTML = getPlaceholderHtml(movie.Name);
            };
            imgContainer.appendChild(img);
        } else {
            imgContainer.innerHTML = getPlaceholderHtml(movie.Name);
        }

        const meta = document.createElement('div');
        meta.className = 'movie-card-meta';
        
        const title = document.createElement('div');
        title.className = 'movie-card-title';
        title.innerText = movie.Name;

        const year = document.createElement('div');
        year.className = 'movie-card-year';
        year.innerText = movie.Jahr || 'k.A.';

        meta.appendChild(title);
        meta.appendChild(year);
        card.appendChild(imgContainer);
        card.appendChild(meta);
        dom.movieGrid.appendChild(card);

        // 2. Render Table Row
        const tr = document.createElement('tr');
        tr.addEventListener('click', (e) => {
            // Don't open details if clicking on action buttons
            if (e.target.closest('.table-actions')) return;
            showMovieDetails(movie);
        });

        tr.innerHTML = `
            <td>${movie.ID}</td>
            <td style="font-weight: 600;">${movie.Name}</td>
            <td>${movie.Jahr || 'k.A.'}</td>
            <td>${movie.Regisseur || 'k.A.'}</td>
            <td>${movie.Genre || 'k.A.'}</td>
            <td>${movie.Laufzeit_min ? movie.Laufzeit_min + ' Min.' : 'k.A.'}</td>
            <td>${movie.Filmreihe || '—'}</td>
            <td>
                <div class="table-actions">
                    <button class="table-action-btn edit-row-btn" title="Bearbeiten">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="table-action-btn delete-row-btn" title="Löschen">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </td>
        `;

        tr.querySelector('.edit-row-btn').addEventListener('click', () => openMovieForm(movie));
        tr.querySelector('.delete-row-btn').addEventListener('click', () => deleteMovie(movie.ID));

        dom.movieTableBody.appendChild(tr);
    });
}

function getPlaceholderHtml(title) {
    return `
        <div class="movie-card-placeholder">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
            <span>${title}</span>
        </div>
    `;
}

function getMediaUrl(dbPath) {
    if (!dbPath) return '';
    if (dbPath.startsWith('http://') || dbPath.startsWith('https://')) {
        return dbPath;
    }
    // Reformat relative paths to communicate with local bottle server media endpoints
    if (dbPath.startsWith('assets/posters/')) {
        return '/media/posters/' + dbPath.replace('assets/posters/', '');
    }
    if (dbPath.startsWith('assets/banners/')) {
        return '/media/banners/' + dbPath.replace('assets/banners/', '');
    }
    return dbPath;
}

// --- Detail View modal logic ---
function showMovieDetails(movie) {
    appState.currentMovie = movie;
    
    document.getElementById('detail-title').innerText = movie.Name;
    document.getElementById('detail-tagline').innerText = movie.Filmreihe ? `Teil der Reihe: ${movie.Filmreihe}` : '';
    document.getElementById('detail-year').innerText = `Jahr: ${movie.Jahr || 'k.A.'}`;
    document.getElementById('detail-runtime').innerText = `Laufzeit: ${movie.Laufzeit_min || '-'} min`;
    
    const fskTag = document.getElementById('detail-fsk');
    if (movie.FSK) {
        fskTag.innerText = `FSK ${movie.FSK}`;
        fskTag.style.display = 'inline-block';
    } else {
        fskTag.style.display = 'none';
    }
    
    document.getElementById('detail-country').innerText = `Land: ${movie.Produktionsland || 'k.A.'}`;
    document.getElementById('detail-description').innerText = movie.Beschreibung || 'Keine Beschreibung vorhanden.';
    document.getElementById('detail-director').innerText = movie.Regisseur || 'k.A.';
    document.getElementById('detail-series').innerText = movie.Filmreihe || '—';
    document.getElementById('detail-genre').innerText = movie.Genre || 'k.A.';
    document.getElementById('detail-studio').innerText = movie.Produktionsfirma || 'k.A.';
    document.getElementById('detail-cast').innerText = movie.Schauspieler || 'Keine Angaben.';
    document.getElementById('detail-voices').innerText = movie.Deutsche_Synchronsprecher || 'Keine Angaben.';

    // Banner and Poster URLs
    const bannerEl = document.getElementById('detail-banner');
    if (movie.Banner_Pfad) {
        bannerEl.src = getMediaUrl(movie.Banner_Pfad);
        bannerEl.style.display = 'block';
    } else {
        bannerEl.src = '';
        bannerEl.style.display = 'none';
    }

    const posterEl = document.getElementById('detail-poster');
    if (movie.Poster_Pfad) {
        posterEl.src = getMediaUrl(movie.Poster_Pfad);
        posterEl.style.display = 'block';
    } else {
        posterEl.src = '';
        posterEl.style.display = 'none';
    }

    openModal('modal-details');
}

// --- Trigger online search if no local matches found ---
async function triggerOnlineSearch() {
    if (!appState.searchQuery.trim()) return;
    
    showLoading("Suche online auf TMDB...");
    try {
        const matches = await pywebview.api.search_online(appState.searchQuery, appState.searchFilter);
        hideLoading();
        
        if (matches && matches.length > 0) {
            renderOnlineMatches(matches);
        } else {
            alert(`Keine Online-Treffer für "${appState.searchQuery}" gefunden.`);
        }
    } catch (e) {
        console.error("Online search failed:", e);
        hideLoading();
    }
}

// --- Render Online search matches list ---
function renderOnlineMatches(matches) {
    const container = document.getElementById('online-matches-list');
    container.innerHTML = '';
    
    matches.forEach(item => {
        const div = document.createElement('div');
        div.className = 'match-item';
        div.addEventListener('click', () => loadOnlineMovieDetails(item.tmdb_id));
        
        let posterImg = '';
        if (item.poster_path) {
            const url = `https://image.tmdb.org/t/p/w92${item.poster_path}`;
            posterImg = `<img src="${url}" class="match-poster" alt="">`;
        } else {
            posterImg = `<div class="match-poster" style="display:flex;align-items:center;justify-content:center;background:#222;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/></svg></div>`;
        }
        
        div.innerHTML = `
            ${posterImg}
            <div class="match-meta">
                <span class="match-title">${item.titel}</span>
                <span class="match-year">${item.jahr || 'k.A.'}</span>
            </div>
        `;
        
        container.appendChild(div);
    });
    
    openModal('modal-online-matches');
}

// --- Load online movie details into form ---
async function loadOnlineMovieDetails(tmdbId) {
    closeModal('modal-online-matches');
    showLoading("Lade Filminformationen von TMDB...");
    
    try {
        const details = await pywebview.api.get_movie_details(tmdbId);
        hideLoading();
        
        if (details) {
            // Fill forms
            openMovieForm({
                ID: '',
                tmdb_id: tmdbId,
                Name: details.titel || '',
                Jahr: details.jahr || '',
                Regisseur: details.regisseur || '',
                Laufzeit_min: details.laufzeit_min || '',
                Genre: details.genre || '',
                Filmreihe: details.filmreihe || '',
                FSK: details.fsk || '',
                Produktionsfirma: details.produktionsfirma || '',
                Produktionsland: details.produktionsland || '',
                Beschreibung: details.beschreibung || '',
                Schauspieler: details.schauspieler || '',
                Deutsche_Synchronsprecher: details.deutsche_synchronsprecher || '',
                Poster_Pfad: details.poster_path || '',
                Banner_Pfad: details.backdrop_path || ''
            });
        }
    } catch (e) {
        console.error("Failed loading TMDB details:", e);
        hideLoading();
    }
}

// --- Open Movie Add/Edit Form ---
function openMovieForm(movie = null) {
    const isEdit = !!movie;
    document.getElementById('movie-form-title').innerText = isEdit ? (movie.ID ? "Film bearbeiten" : "Film hinzufügen") : "Film hinzufügen";
    
    document.getElementById('form-movie-id').value = (movie && movie.ID) || '';
    document.getElementById('form-tmdb-id').value = (movie && movie.tmdb_id) || '';
    
    document.getElementById('form-title').value = (movie && movie.Name) || '';
    document.getElementById('form-year').value = (movie && movie.Jahr) || '';
    document.getElementById('form-director').value = (movie && movie.Regisseur) || '';
    document.getElementById('form-runtime').value = (movie && movie.Laufzeit_min) || '';
    document.getElementById('form-genre').value = (movie && movie.Genre) || '';
    document.getElementById('form-series').value = (movie && movie.Filmreihe) || '';
    document.getElementById('form-fsk').value = (movie && movie.FSK) || '';
    document.getElementById('form-studio').value = (movie && movie.Produktionsfirma) || '';
    document.getElementById('form-country').value = (movie && movie.Produktionsland) || '';
    document.getElementById('form-description').value = (movie && movie.Beschreibung) || '';
    document.getElementById('form-cast').value = (movie && movie.Schauspieler) || '';
    document.getElementById('form-voices').value = (movie && movie.Deutsche_Synchronsprecher) || '';
    
    document.getElementById('form-poster').value = (movie && movie.Poster_Pfad) || '';
    document.getElementById('form-banner').value = (movie && movie.Banner_Pfad) || '';
    
    openModal('modal-movie-form');
}

// --- Browse file for poster/banner ---
async function browseAsset(imgType) {
    try {
        const filePath = await pywebview.api.select_image_file();
        if (filePath) {
            showLoading("Kopiere Bild...");
            const res = await pywebview.api.copy_image_to_media(filePath, imgType);
            hideLoading();
            
            if (res.success) {
                document.getElementById(`form-${imgType}`).value = res.path;
            } else {
                alert("Fehler beim Kopieren: " + res.error);
            }
        }
    } catch (e) {
        console.error("Browse asset failed:", e);
        hideLoading();
    }
}

// --- Submit Movie Form ---
async function submitMovieForm(event) {
    event.preventDefault();
    
    const movieId = document.getElementById('form-movie-id').value;
    const tmdbId = document.getElementById('form-tmdb-id').value;
    
    const movieData = {
        tmdb_id: tmdbId || null,
        Name: document.getElementById('form-title').value,
        Jahr: parseInt(document.getElementById('form-year').value) || null,
        Regisseur: document.getElementById('form-director').value || null,
        Laufzeit_min: parseInt(document.getElementById('form-runtime').value) || null,
        Genre: document.getElementById('form-genre').value || null,
        Filmreihe: document.getElementById('form-series').value || null,
        FSK: document.getElementById('form-fsk').value || null,
        Produktionsfirma: document.getElementById('form-studio').value || null,
        Produktionsland: document.getElementById('form-country').value || null,
        Beschreibung: document.getElementById('form-description').value || null,
        Schauspieler: document.getElementById('form-cast').value || null,
        Deutsche_Synchronsprecher: document.getElementById('form-voices').value || null,
        Poster_Pfad: document.getElementById('form-poster').value || null,
        Banner_Pfad: document.getElementById('form-banner').value || null
    };
    
    showLoading("Speichere Film...");
    try {
        let res;
        if (movieId) {
            res = await pywebview.api.update_movie(parseInt(movieId), movieData);
        } else {
            res = await pywebview.api.add_movie(movieData);
        }
        
        hideLoading();
        if (res.success) {
            closeModal('modal-movie-form');
            await refreshMovies();
            // If details modal was open for this movie, update details view or close
            closeModal('modal-details');
        } else {
            alert("Fehler beim Speichern: " + res.error);
        }
    } catch (e) {
        console.error("Saving movie failed:", e);
        hideLoading();
    }
}

// --- Delete movie from database ---
async function deleteMovie(movieId) {
    if (!confirm("Möchten Sie diesen Film wirklich dauerhaft löschen?")) return;
    
    showLoading("Lösche Film...");
    try {
        const res = await pywebview.api.delete_movie(movieId);
        hideLoading();
        if (res.success) {
            closeModal('modal-details');
            await refreshMovies();
        } else {
            alert("Fehler beim Löschen: " + res.error);
        }
    } catch (e) {
        console.error("Deleting failed:", e);
        hideLoading();
    }
}

// --- Settings Overlay Functions ---
function openSettings() {
    document.getElementById('settings-tmdb-key').value = appState.config.api_key || '';
    document.getElementById('settings-github-token').value = appState.config.github_token || '';
    document.getElementById('settings-theme').value = appState.config.theme || 'cyan';
    document.getElementById('settings-view').value = appState.config.default_view || 'Galerie';
    document.getElementById('settings-path').value = appState.config.custom_media_path || '';
    
    openModal('modal-settings');
}

async function browseCustomPath() {
    try {
        const folder = await pywebview.api.select_folder();
        if (folder) {
            document.getElementById('settings-path').value = folder;
        }
    } catch (e) {
        console.error("Browse path error:", e);
    }
}

async function testAPIConnections() {
    const tmdbKey = document.getElementById('settings-tmdb-key').value.trim();
    const ghToken = document.getElementById('settings-github-token').value.trim();
    
    showLoading("Verbindungen werden getestet...");
    
    let tmdbOk = false;
    let ghOk = false;
    
    // Test TMDB
    if (tmdbKey) {
        try {
            const url = "https://api.themoviedb.org/3/configuration";
            const headers = tmdbKey.length > 50 || tmdbKey.startswith?.("eyJ") ? 
                {"Authorization": `Bearer ${tmdbKey}`} : {};
            const params = tmdbKey.length > 50 || tmdbKey.startswith?.("eyJ") ? 
                {} : {"api_key": tmdbKey};
                
            // Note: Since JS runs locally, we can make calls using standard fetch!
            // Wait, fetch Configuration
            const fullUrl = url + (params.api_key ? `?api_key=${params.api_key}` : '');
            const options = headers.Authorization ? { headers } : {};
            const resp = await fetch(fullUrl, options);
            if (resp.status === 200) tmdbOk = true;
        } catch(e) {}
    } else {
        tmdbOk = true; // No key to test is fine
    }

    // Test GitHub
    if (ghToken) {
        try {
            const resp = await fetch("https://api.github.com/repos/TentixTV/CinepalastManager", {
                headers: {"Authorization": `token ${ghToken}`}
            });
            if (resp.status === 200) ghOk = true;
        } catch(e) {}
    } else {
        ghOk = true;
    }
    
    hideLoading();
    if (tmdbOk && ghOk) {
        alert("Verbindungstest erfolgreich!");
    } else {
        alert(`Verbindungstest fehlgeschlagen:\nTMDB: ${tmdbOk ? 'OK' : 'Fehler'}\nGitHub: ${ghOk ? 'OK' : 'Fehler'}`);
    }
}

async function saveSettings(event) {
    event.preventDefault();
    
    const newPath = document.getElementById('settings-path').value.trim();
    const oldPath = appState.config.custom_media_path || '';
    
    const newConfig = {
        api_key: document.getElementById('settings-tmdb-key').value.trim(),
        github_token: document.getElementById('settings-github-token').value.trim(),
        theme: document.getElementById('settings-theme').value,
        default_view: document.getElementById('settings-view').value,
        custom_media_path: newPath
    };
    
    if (newPath !== oldPath) {
        if (confirm("Sie haben den Speicherpfad geändert. Möchten Sie alle vorhandenen Bilder (Poster & Banner) in das neue Verzeichnis kopieren?")) {
            showLoading("Kopiere Mediendateien...");
            const resCopy = await pywebview.api.copy_existing_media_files(newPath);
            hideLoading();
            if (resCopy.success) {
                alert(`${resCopy.copied} Mediendateien wurden erfolgreich kopiert.`);
            } else {
                alert("Fehler beim Kopieren der Medien: " + resCopy.error);
            }
        }
    }
    
    showLoading("Speichere Einstellungen...");
    try {
        const res = await pywebview.api.save_config(newConfig);
        hideLoading();
        
        if (res.success) {
            appState.config = newConfig;
            applyTheme(newConfig.theme);
            setViewMode(newConfig.default_view);
            closeModal('modal-settings');
            await refreshMovies();
        } else {
            alert("Fehler beim Speichern der Einstellungen: " + res.error);
        }
    } catch(e) {
        console.error("Save settings error:", e);
        hideLoading();
    }
}

async function backupDatabase() {
    try {
        const res = await pywebview.api.backup_database();
        if (res.success) {
            alert("Backup erfolgreich gespeichert unter:\n" + res.path);
        } else if (res.error) {
            alert("Backup fehlgeschlagen: " + res.error);
        }
    } catch (e) {
        console.error(e);
    }
}

async function restoreDatabase() {
    if (!confirm("ACHTUNG: Beim Laden eines Backups wird die aktuelle Datenbank überschrieben. Fortfahren?")) return;
    
    showLoading("Backup wird geladen...");
    try {
        const res = await pywebview.api.restore_database();
        hideLoading();
        if (res.success) {
            alert("Datenbank erfolgreich wiederhergestellt!");
            closeModal('modal-settings');
            await refreshMovies();
        } else if (res.error) {
            alert("Wiederherstellung fehlgeschlagen: " + res.error);
        }
    } catch(e) {
        console.error(e);
        hideLoading();
    }
}

async function resetDatabase() {
    if (!confirm("ACHTUNG: Möchten Sie wirklich alle Filme unwiderruflich aus der Datenbank löschen?")) return;
    
    showLoading("Setze Datenbank zurück...");
    try {
        const res = await pywebview.api.reset_database();
        hideLoading();
        if (res.success) {
            alert("Datenbank erfolgreich geleert!");
            closeModal('modal-settings');
            await refreshMovies();
        } else {
            alert("Fehler: " + res.error);
        }
    } catch(e) {
        console.error(e);
        hideLoading();
    }
}

// --- Generic Modal helpers ---
function openModal(id) {
    const modal = document.getElementById(id);
    modal.style.display = 'flex';
    // Small delay to trigger CSS transition
    setTimeout(() => {
        modal.classList.add('active');
    }, 10);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    modal.classList.remove('active');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 250);
}
